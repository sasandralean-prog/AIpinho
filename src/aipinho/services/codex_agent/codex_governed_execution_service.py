from __future__ import annotations

import fnmatch
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.codex_governed_execution import (
    CodexGovernedAction,
    CodexGovernedActionRequest,
    CodexGovernedContract,
    CodexGovernedContractDecision,
    CodexGovernedContractRequest,
    CodexGovernedProposalRequest,
)
from aipinho.schemas.codex_agent import CodexRunEvent
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.events.contracts import EventPublishRequest, utc_now_iso
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.codex_agent.codex_governed_contract_store import (
    CodexGovernedContractStore,
)
from aipinho.services.codex_agent.codex_agent_config_service import (
    CodexAgentConfigService,
)
from aipinho.services.codex_agent.codex_agent_store import CodexAgentStore
from aipinho.services.codex_agent.codex_cli_adapter import CodexCliAdapter
from aipinho.services.events.event_core import EventPublisherService, redact_payload
from aipinho.services.patching.apply.atomic_patch_write_service import (
    AtomicPatchWriteService,
)
from aipinho.services.patching.apply.patch_apply_backup_service import (
    PatchApplyBackupService,
)
from aipinho.services.patching.apply.patch_apply_hashing import sha256_file
from aipinho.services.policy_kernel.workspace_role_contract_service import (
    WorkspaceRoleContractService,
)
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.services.tools.governed_tool_execution_service import (
    GovernedToolExecutionService,
)
from aipinho.services.tools.write_capability_envelope_service import (
    WriteCapabilityEnvelopeService,
)
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class CodexGovernedExecutionService:
    def __init__(
        self,
        *,
        store: CodexGovernedContractStore | None = None,
        approvals: ApprovalService | None = None,
        tool_execution: GovernedToolExecutionService | None = None,
        policy_path: Path | None = None,
        workspace_roles: WorkspaceRoleContractService | None = None,
        envelopes: WriteCapabilityEnvelopeService | None = None,
        atomic_writer: AtomicPatchWriteService | None = None,
        backups: PatchApplyBackupService | None = None,
        config_service: CodexAgentConfigService | None = None,
        cli_adapter: Any | None = None,
        codex_store: CodexAgentStore | None = None,
    ) -> None:
        self.store = store or CodexGovernedContractStore()
        self.approvals = approvals or ApprovalService()
        self.tool_execution = tool_execution or GovernedToolExecutionService(
            approvals=self.approvals
        )
        self.policy_path = (
            policy_path
            or PATHS.config_root
            / "codex_agent"
            / "codex_governed_execution_policy.yaml"
        )
        self.policy = load_yaml_file(
            self.policy_path, critical=True, root=self.policy_path.parent
        )
        self.workspace_roles = workspace_roles or WorkspaceRoleContractService().load()
        self.envelopes = envelopes or WriteCapabilityEnvelopeService(
            workspace_roles=self.workspace_roles
        )
        self.atomic_writer = atomic_writer or AtomicPatchWriteService()
        self.backups = backups or PatchApplyBackupService()
        self.config_service = config_service or CodexAgentConfigService()
        self.cli_adapter = cli_adapter
        self.codex_store = codex_store or CodexAgentStore()
        self.secret_guard = SecretGuardService()

    def propose_contract(
        self, request: CodexGovernedProposalRequest
    ) -> CodexGovernedContract:
        config = self.config_service.runtime()
        status = self.config_service.status()
        adapter = self.cli_adapter or CodexCliAdapter(status.cli_status)
        proposal = adapter.run_governed_proposal(
            prompt=request.prompt,
            config=config,
            workdir=request.workspace_path,
            output_schema_path=(
                PATHS.config_root
                / "codex_agent"
                / "governed_contract_output.schema.json"
            ),
        )
        if proposal.result.status != "completed" or proposal.payload is None:
            raise ValueError(
                proposal.result.error_code or "codex_governed_proposal_failed"
            )
        actions_payload = proposal.payload.get("actions")
        if not isinstance(actions_payload, list):
            raise ValueError("codex_governed_proposal_actions_invalid")
        actions = [
            CodexGovernedActionRequest.model_validate(item)
            for item in actions_payload
            if isinstance(item, dict)
        ]
        if len(actions) != len(actions_payload):
            raise ValueError("codex_governed_proposal_action_invalid")
        objective = str(proposal.payload.get("objective") or request.prompt)
        return self.create_contract(
            CodexGovernedContractRequest(
                session_id=request.session_id,
                run_id=request.run_id,
                objective=objective,
                workspace_path=request.workspace_path,
                actions=actions,
                requested_by=request.requested_by,
                metadata={
                    **request.metadata,
                    "proposal_source": "codex_cli_read_only",
                    "proposal_cli_status": proposal.result.cli_status,
                    "proposal_event_count": proposal.result.event_count,
                    "proposal_latency_ms": proposal.result.latency_ms,
                },
            )
        )

    def create_contract(
        self, request: CodexGovernedContractRequest
    ) -> CodexGovernedContract:
        settings = self._settings()
        blocked: list[str] = []
        warnings: list[str] = []
        if not settings.get("enabled", False):
            blocked.append("codex_governed_execution_disabled")
        if not request.actions:
            blocked.append("contract_actions_required")
        if len(request.actions) > self._limit("max_actions_per_contract", 40):
            blocked.append("contract_action_limit_exceeded")

        workspace = self.workspace_roles.resolve(request.workspace_path)
        contract_role = workspace.contract.role if workspace.contract else None
        workspace_id = workspace.contract.workspace_id if workspace.contract else None
        allowed_roles = {
            str(item)
            for item in settings.get(
                "allowed_workspace_roles", ["target_mutable", "system_mutable"]
            )
            or []
        }
        if workspace.status != "allowed" or workspace.contract is None:
            blocked.append(workspace.reason)
        elif contract_role not in allowed_roles:
            blocked.append("workspace_role_not_allowed_for_codex_execution")

        actions: list[CodexGovernedAction] = []
        file_count = 0
        shell_count = 0
        total_content_chars = 0
        for sequence, item in enumerate(request.actions, start=1):
            action, action_blocked, action_warnings = self._build_action(
                request, item, sequence
            )
            actions.append(action)
            blocked.extend(action_blocked)
            warnings.extend(action_warnings)
            if item.action_type in {"create_file", "modify_file"}:
                file_count += 1
                total_content_chars += len(item.content or "")
            elif item.action_type == "run_shell":
                shell_count += 1

        if file_count > self._limit("max_file_actions_per_contract", 30):
            blocked.append("contract_file_action_limit_exceeded")
        if shell_count > self._limit("max_shell_actions_per_contract", 10):
            blocked.append("contract_shell_action_limit_exceeded")
        if total_content_chars > self._limit("max_total_content_chars", 4_000_000):
            blocked.append("contract_total_content_limit_exceeded")

        fingerprint = self._contract_fingerprint(
            objective=request.objective,
            workspace_path=request.workspace_path,
            action_fingerprints=[action.action_fingerprint for action in actions],
        )
        ttl = max(
            1,
            min(
                int(
                    request.expires_in_minutes
                    or settings.get("contract_ttl_minutes", 60)
                ),
                24 * 60,
            ),
        )
        contract = CodexGovernedContract(
            session_id=request.session_id,
            run_id=request.run_id,
            objective=request.objective,
            workspace_path=request.workspace_path,
            workspace_id=workspace_id,
            workspace_role=contract_role,
            status="blocked" if blocked else "preview",
            actions=actions,
            contract_fingerprint=fingerprint,
            safe_to_execute=False,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=list(dict.fromkeys(blocked)),
            requested_by=request.requested_by,
            metadata={
                **request.metadata,
                "policy_schema_version": int(
                    self.policy.get("schema_version", 1) or 1
                ),
                "workspace_trace": workspace.trace,
                "file_action_count": file_count,
                "shell_action_count": shell_count,
            },
            expires_at=(
                datetime.now(timezone.utc) + timedelta(minutes=ttl)
            ).isoformat(),
        )
        contract = self.store.save(contract)
        self._publish(
            "codex_governed_contract_created",
            "Contrato governado Codex criado sem executar efeitos colaterais.",
            {
                "contract_id": contract.contract_id,
                "session_id": contract.session_id,
                "status": contract.status,
                "workspace_id": contract.workspace_id,
                "action_count": len(contract.actions),
                "blocked_reasons": contract.blocked_reasons,
            },
            status=contract.status,
        )
        return contract

    def request_approval(
        self, contract_id: str
    ) -> CodexGovernedContractDecision:
        contract = self._required_contract(contract_id)
        self._ensure_not_expired(contract)
        if contract.status == "blocked" or contract.blocked_reasons:
            return CodexGovernedContractDecision(
                status="blocked",
                contract=contract,
                message="Contrato bloqueado pela policy; nenhuma approval foi criada.",
            )
        if contract.status not in {"preview", "approval_pending"}:
            raise ValueError(f"contract_not_approvable:{contract.status}")
        self._ensure_contract_integrity(contract)

        approvals: list[dict[str, Any]] = []
        updated_actions: list[CodexGovernedAction] = []
        for action in contract.actions:
            if action.approval_id:
                approval = self.approvals.get_approval(action.approval_id)
                if approval is not None:
                    approvals.append(approval.model_dump())
                    updated_actions.append(
                        action.model_copy(update={"approval_status": approval.status})
                    )
                    continue
            if action.action_type == "run_shell":
                response = self.tool_execution.request_approval(
                    self._shell_request(contract, action)
                )
                approval = response.get("approval")
                if approval is None:
                    reasons = list(
                        getattr(response.get("result"), "violations", [])
                    )
                    blocked_action = action.model_copy(
                        update={
                            "status": "blocked",
                            "blocked_reasons": reasons
                            or ["shell_approval_request_blocked"],
                        }
                    )
                    updated_actions.append(blocked_action)
                    continue
                approval_payload = approval.model_dump()
            else:
                approval = self._create_file_approval(contract, action)
                approval_payload = approval.model_dump()
            approvals.append(approval_payload)
            updated_actions.append(
                action.model_copy(
                    update={
                        "status": "approval_pending",
                        "approval_id": approval_payload["approval_id"],
                        "approval_status": approval_payload["status"],
                    }
                )
            )

        blocked = [
            reason
            for action in updated_actions
            for reason in action.blocked_reasons
        ]
        contract = contract.model_copy(
            update={
                "actions": updated_actions,
                "approval_ids": [
                    str(item["approval_id"]) for item in approvals
                ],
                "status": "blocked" if blocked else "approval_pending",
                "blocked_reasons": list(dict.fromkeys(blocked)),
                "safe_to_execute": False,
            }
        )
        contract = self.store.save(contract)
        self._publish(
            "codex_governed_contract_approval_requested",
            "Approvals exatas foram criadas para as acoes do contrato Codex.",
            {
                "contract_id": contract.contract_id,
                "approval_ids": contract.approval_ids,
                "status": contract.status,
            },
            status=contract.status,
        )
        return CodexGovernedContractDecision(
            status=contract.status,
            contract=contract,
            approvals=approvals,
            message=(
                "Aprovacao pendente para cada efeito colateral."
                if contract.status == "approval_pending"
                else "A criacao de approval foi bloqueada pela policy."
            ),
        )

    def refresh_approval_state(self, contract_id: str) -> CodexGovernedContract:
        contract = self._required_contract(contract_id)
        updated_actions: list[CodexGovernedAction] = []
        statuses: list[str] = []
        for action in contract.actions:
            approval = (
                self.approvals.get_approval(action.approval_id)
                if action.approval_id
                else None
            )
            status = approval.status if approval else action.approval_status
            statuses.append(str(status or "missing"))
            updated_actions.append(action.model_copy(update={"approval_status": status}))
        if statuses and all(status == "approved" for status in statuses):
            next_status = "approved"
            safe_to_execute = True
        elif any(status in {"rejected", "cancelled", "expired"} for status in statuses):
            next_status = "blocked"
            safe_to_execute = False
        else:
            next_status = "approval_pending"
            safe_to_execute = False
        return self.store.save(
            contract.model_copy(
                update={
                    "actions": updated_actions,
                    "status": next_status,
                    "safe_to_execute": safe_to_execute,
                }
            )
        )

    def execute(self, contract_id: str) -> CodexGovernedContract:
        contract = self.refresh_approval_state(contract_id)
        self._ensure_not_expired(contract)
        self._ensure_contract_integrity(contract)
        if contract.status != "approved" or not contract.safe_to_execute:
            raise ValueError("contract_not_approved")

        preflight_reasons = self._execution_preflight(contract)
        if preflight_reasons:
            return self.store.save(
                contract.model_copy(
                    update={
                        "status": "blocked",
                        "safe_to_execute": False,
                        "blocked_reasons": preflight_reasons,
                    }
                )
            )

        contract = self.store.save(
            contract.model_copy(
                update={"status": "executing", "validation_status": "running"}
            )
        )
        self._publish(
            "codex_governed_contract_execution_started",
            "Execucao governada Codex iniciada apos approvals validas.",
            {"contract_id": contract.contract_id},
            status="executing",
        )

        executed_files: list[dict[str, Any]] = []
        updated_actions: list[CodexGovernedAction] = []
        failed = False
        for action in contract.actions:
            try:
                if action.action_type == "run_shell":
                    result = self.tool_execution.execute(
                        self._shell_request(
                            contract, action, approval_id=action.approval_id
                        )
                    )
                    action_result = result.model_dump()
                    success = result.status == "executed_governed" and (
                        result.metadata.get("exit_code") in {None, 0}
                    )
                else:
                    action_result, rollback = self._execute_file_action(
                        contract, action
                    )
                    executed_files.append(rollback)
                    success = bool(action_result.get("validated"))
                updated_actions.append(
                    action.model_copy(
                        update={
                            "status": "completed" if success else "failed",
                            "result": redact_payload(action_result),
                        }
                    )
                )
                if not success:
                    failed = True
                    if self._settings().get("stop_on_action_failure", True):
                        break
            except Exception as exc:
                updated_actions.append(
                    action.model_copy(
                        update={
                            "status": "failed",
                            "blocked_reasons": [self._safe_error_code(exc)],
                        }
                    )
                )
                failed = True
                break

        if failed and self._settings().get("rollback_on_file_failure", True):
            self._rollback_files(executed_files)

        if len(updated_actions) < len(contract.actions):
            executed_ids = {action.action_id for action in updated_actions}
            updated_actions.extend(
                action.model_copy(update={"status": "cancelled"})
                for action in contract.actions
                if action.action_id not in executed_ids
            )

        all_completed = all(
            action.status == "completed" for action in updated_actions
        )
        validation_status = "passed" if all_completed else "failed"
        final_status = "completed" if all_completed else "failed"
        contract = self.store.save(
            contract.model_copy(
                update={
                    "actions": updated_actions,
                    "status": final_status,
                    "validation_status": validation_status,
                    "safe_to_execute": False,
                    "safe_to_report_success": all_completed,
                    "execution_summary": {
                        "completed_actions": sum(
                            action.status == "completed"
                            for action in updated_actions
                        ),
                        "failed_actions": sum(
                            action.status == "failed" for action in updated_actions
                        ),
                        "rolled_back": bool(failed and executed_files),
                    },
                }
            )
        )
        self._publish(
            "codex_governed_contract_execution_finished",
            (
                "Execucao governada Codex concluida e validada."
                if all_completed
                else "Execucao governada Codex falhou; alteracoes de arquivo foram reconciliadas."
            ),
            {
                "contract_id": contract.contract_id,
                "status": contract.status,
                "validation_status": contract.validation_status,
                "summary": contract.execution_summary,
            },
            status=contract.status,
            severity="info" if all_completed else "warning",
        )
        return contract

    def get(self, contract_id: str) -> CodexGovernedContract | None:
        return self.store.get(contract_id)

    def list(self, *, session_id: str | None = None) -> list[CodexGovernedContract]:
        return self.store.list(session_id=session_id)

    def cancel(self, contract_id: str) -> CodexGovernedContract:
        contract = self._required_contract(contract_id)
        if contract.status in {"executing", "validating", "completed", "failed"}:
            raise ValueError("contract_not_cancellable")
        for approval_id in contract.approval_ids:
            approval = self.approvals.get_approval(approval_id)
            if approval and approval.status == "pending":
                self.approvals.cancel(
                    approval_id,
                    actor=Actor(type="user", id=contract.requested_by),
                    reason="codex_governed_contract_cancelled",
                )
        return self.store.save(
            contract.model_copy(
                update={"status": "cancelled", "safe_to_execute": False}
            )
        )

    def status(self) -> dict[str, Any]:
        settings = self._settings()
        return {
            "status": "ok" if settings.get("enabled", False) else "disabled",
            "service": "codex_governed_execution",
            "schema_version": self.policy.get("schema_version", 1),
            "allowed_action_types": list(
                settings.get("allowed_action_types", []) or []
            ),
            "approval_required_for_every_action": bool(
                settings.get("require_approval_for_every_action", True)
            ),
            "post_validation_required": bool(
                settings.get("require_post_validation", True)
            ),
            "shell_free": False,
            "direct_unreviewed_write": False,
        }

    def public_contract(
        self, contract: CodexGovernedContract, *, include_content: bool = False
    ) -> dict[str, Any]:
        payload = contract.model_dump()
        if include_content:
            return redact_payload(payload)
        for action in payload.get("actions", []):
            if not isinstance(action, dict):
                continue
            content = action.get("content")
            if isinstance(content, str):
                action["content"] = None
                metadata = action.get("metadata")
                if not isinstance(metadata, dict):
                    metadata = {}
                    action["metadata"] = metadata
                metadata["content_available_on_explicit_request"] = True
                metadata["content_chars"] = len(content)
        return redact_payload(payload)

    def _build_action(
        self,
        request: CodexGovernedContractRequest,
        item: CodexGovernedActionRequest,
        sequence: int,
    ) -> tuple[CodexGovernedAction, list[str], list[str]]:
        settings = self._settings()
        blocked: list[str] = []
        warnings: list[str] = []
        if item.action_type not in set(
            settings.get("allowed_action_types", []) or []
        ):
            blocked.append("codex_action_type_not_allowed")

        target_path: str | None = None
        content_hash: str | None = None
        original_hash: str | None = None
        policy_decision: dict[str, Any] = {}
        timeout = item.timeout_seconds
        if item.action_type in {"create_file", "modify_file"}:
            assert item.target_path is not None
            target = self._target_path(request.workspace_path, item.target_path)
            target_path = str(target)
            if self.secret_guard.is_secret_path(target):
                blocked.append("secret_target_path_blocked")
            if self._filename_blocked(target.name):
                blocked.append("target_filename_blocked_by_policy")
            if target.suffix.lower() in {
                str(value).lower()
                for value in settings.get("blocked_extensions", []) or []
            }:
                blocked.append("target_extension_blocked_by_policy")
            content = item.content or ""
            if len(content) > self._limit("max_file_content_chars", 1_000_000):
                blocked.append("file_content_limit_exceeded")
            _redacted, secret_warnings = self.secret_guard.redact(content)
            if secret_warnings:
                blocked.append("secret_content_detected")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if item.action_type == "create_file" and target.exists():
                blocked.append("create_target_already_exists")
            if item.action_type == "modify_file" and not target.is_file():
                blocked.append("modify_target_missing")
            if target.is_file():
                original_hash = sha256_file(target)
            envelope = self.envelopes.create(
                workspace_path=request.workspace_path,
                operation_type=item.action_type,
                target_path=target_path,
                task_id=request.run_id,
                session_id=request.session_id,
                preview_id="codex_contract_preview_pending",
                approval_id="codex_contract_approval_pending",
                expected_side_effects=item.expected_side_effects
                or [f"{item.action_type}:{target_path}"],
                actor="codex_agent",
            )
            policy_decision = envelope.model_dump()
            if not envelope.allowed:
                blocked.extend(envelope.envelope.blocking_reasons)
        else:
            timeout = max(
                1,
                min(
                    int(
                        timeout
                        or self._settings().get("max_shell_timeout_seconds", 120)
                    ),
                    self._limit("max_shell_timeout_seconds", 120),
                ),
            )
            preview_request = ToolExecutionRequest(
                tool_execution_request_id=f"codex_shell_preview_{sequence}",
                tool_id="shell.run_command",
                input={
                    "workspace": request.workspace_path,
                    "argv": item.argv,
                    "timeout_seconds": timeout,
                },
                session_id=request.session_id,
                draft_id=request.run_id,
                preview_id="codex_contract_preview_pending",
                mode="governed",
                requested_by=Actor(type="user", id=request.requested_by),
            )
            decision = self.tool_execution.preview_decision(preview_request)
            policy_decision = redact_payload(decision)
            if not decision.get("allowed"):
                blocked.extend(
                    str(value) for value in decision.get("violations", []) or []
                )
            warnings.extend(
                str(value) for value in decision.get("warnings", []) or []
            )

        fingerprint = self._action_fingerprint(
            action_type=item.action_type,
            workspace_path=request.workspace_path,
            target_path=target_path,
            content_sha256=content_hash,
            original_sha256=original_hash,
            argv=item.argv,
            timeout_seconds=timeout,
        )
        return (
            CodexGovernedAction(
                sequence=sequence,
                action_type=item.action_type,
                workspace_path=request.workspace_path,
                target_path=target_path,
                content=item.content,
                content_sha256=content_hash,
                original_sha256=original_hash,
                argv=item.argv,
                timeout_seconds=timeout,
                expected_side_effects=item.expected_side_effects,
                validation_required=item.validation_required,
                action_fingerprint=fingerprint,
                policy_decision=policy_decision,
                warnings=list(dict.fromkeys(warnings)),
                blocked_reasons=list(dict.fromkeys(blocked)),
                metadata=item.metadata,
            ),
            blocked,
            warnings,
        )

    def _create_file_approval(
        self, contract: CodexGovernedContract, action: CodexGovernedAction
    ) -> ApprovalRequest:
        now = datetime.now(timezone.utc)
        approval = ApprovalRequest(
            approval_id=f"approval_codex_{action.action_id}",
            preview_id=contract.contract_id,
            draft_id=contract.run_id or contract.contract_id,
            session_id=contract.session_id,
            status="pending",
            actions_requested=[action.action_type],
            approval_scope="future_execution",
            reason=(
                f"Codex governed {action.action_type} requested for an exact "
                "workspace-relative target."
            ),
            risk_level="medium",
            policy_snapshot=ApprovalPolicySnapshot(
                policy_status="approval_required",
                allowed_actions=[action.action_type],
                denied_actions=["delete_file", "move_file", "git_write"],
                approval_required_for=[action.action_type],
                granted_capabilities=["write_workspace"],
                denied_capabilities=["git", "unrestricted_shell"],
                workspace_status=contract.workspace_role or "unknown",
                risk_level="medium",
                trace_hash=contract.contract_fingerprint,
                config_versions={
                    "codex_governed_execution_policy": int(
                        self.policy.get("schema_version", 1) or 1
                    ),
                    "codex_contract_id": contract.contract_id,
                    "codex_contract_fingerprint": contract.contract_fingerprint,
                    "codex_action_id": action.action_id,
                    "codex_action_fingerprint": action.action_fingerprint,
                },
            ),
            expires_at=contract.expires_at,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=Actor(type="user", id=contract.requested_by),
            trace=[
                {
                    "stage": "codex_governed_contract_approval",
                    "decision": "pending",
                    "reason": "exact_file_action_requires_approval",
                    "contract_id": contract.contract_id,
                    "action_id": action.action_id,
                }
            ],
            execution_status="not_executed",
        )
        self.approvals.store.save(approval)
        self.approvals.append_event(
            approval.approval_id,
            "approval_created",
            "Approval criada para uma acao de arquivo Codex exata; nada foi escrito.",
            data={
                "contract_id": contract.contract_id,
                "action_id": action.action_id,
                "action_type": action.action_type,
            },
        )
        return approval

    def _execution_preflight(
        self, contract: CodexGovernedContract
    ) -> list[str]:
        reasons: list[str] = []
        for action in contract.actions:
            approval = (
                self.approvals.get_approval(action.approval_id)
                if action.approval_id
                else None
            )
            if approval is None:
                reasons.append(f"{action.action_id}:approval_missing")
                continue
            if approval.status != "approved":
                reasons.append(
                    f"{action.action_id}:approval_not_approved:{approval.status}"
                )
                continue
            if action.action_type in {"create_file", "modify_file"}:
                approved_fingerprint = str(
                    approval.policy_snapshot.config_versions.get(
                        "codex_action_fingerprint"
                    )
                    or ""
                )
                if approved_fingerprint != action.action_fingerprint:
                    reasons.append(f"{action.action_id}:approval_fingerprint_mismatch")
                target = Path(action.target_path or "")
                if action.action_type == "create_file" and target.exists():
                    reasons.append(f"{action.action_id}:create_target_now_exists")
                if action.action_type == "modify_file":
                    if not target.is_file():
                        reasons.append(f"{action.action_id}:modify_target_missing")
                    elif sha256_file(target) != action.original_sha256:
                        reasons.append(f"{action.action_id}:target_changed_after_preview")
        return list(dict.fromkeys(reasons))

    def _execute_file_action(
        self, contract: CodexGovernedContract, action: CodexGovernedAction
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        assert action.target_path is not None
        assert action.content is not None
        envelope = self.envelopes.create(
            workspace_path=contract.workspace_path,
            operation_type=action.action_type,
            target_path=action.target_path,
            task_id=contract.run_id,
            session_id=contract.session_id,
            preview_id=contract.contract_id,
            approval_id=action.approval_id,
            expected_side_effects=action.expected_side_effects
            or [f"{action.action_type}:{action.target_path}"],
            actor="codex_agent",
        )
        if not envelope.allowed:
            raise ValueError(
                "write_envelope_blocked:"
                + ",".join(envelope.envelope.blocking_reasons)
        )
        target = Path(action.target_path)
        backup = (
            self.backups.create_backup(target, contract.contract_id)
            if action.action_type == "modify_file"
            else None
        )
        try:
            written_hash = self.atomic_writer.write(target, action.content)
            logical_hash = hashlib.sha256(
                target.read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest()
            validated = logical_hash == action.content_sha256 and target.is_file()
            if not validated:
                raise ValueError("post_write_hash_validation_failed")
        except Exception:
            if backup is not None:
                self.backups.restore_backup(backup, target)
            elif target.exists() and target.is_file():
                target.unlink()
            raise
        return (
            {
                "target_path": str(target),
                "written_sha256": written_hash,
                "logical_content_sha256": logical_hash,
                "validated": True,
                "backup_id": backup.backup_id if backup else None,
            },
            {
                "target_path": str(target),
                "action_type": action.action_type,
                "backup": backup,
            },
        )

    def _rollback_files(self, entries: list[dict[str, Any]]) -> None:
        for entry in reversed(entries):
            target = Path(str(entry["target_path"]))
            backup = entry.get("backup")
            try:
                if backup is not None:
                    self.backups.restore_backup(backup, target)
                elif (
                    entry.get("action_type") == "create_file"
                    and target.exists()
                    and target.is_file()
                ):
                    target.unlink()
            except Exception:
                continue

    def _shell_request(
        self,
        contract: CodexGovernedContract,
        action: CodexGovernedAction,
        *,
        approval_id: str | None = None,
    ) -> ToolExecutionRequest:
        return ToolExecutionRequest(
            tool_execution_request_id=action.action_id,
            tool_id="shell.run_command",
            input={
                "workspace": contract.workspace_path,
                "argv": action.argv,
                "timeout_seconds": action.timeout_seconds,
            },
            session_id=contract.session_id,
            draft_id=contract.run_id or contract.contract_id,
            preview_id=contract.contract_id,
            approval_id=approval_id,
            mode="governed",
            requested_by=Actor(type="user", id=contract.requested_by),
        )

    def _ensure_contract_integrity(self, contract: CodexGovernedContract) -> None:
        expected = self._contract_fingerprint(
            objective=contract.objective,
            workspace_path=contract.workspace_path,
            action_fingerprints=[
                action.action_fingerprint for action in contract.actions
            ],
        )
        if expected != contract.contract_fingerprint:
            raise ValueError("codex_contract_fingerprint_mismatch")
        for action in contract.actions:
            if action.action_type in {"create_file", "modify_file"}:
                current_content_hash = hashlib.sha256(
                    (action.content or "").encode("utf-8")
                ).hexdigest()
                if current_content_hash != action.content_sha256:
                    raise ValueError(
                        f"codex_action_content_hash_mismatch:{action.action_id}"
                    )
            current = self._action_fingerprint(
                action_type=action.action_type,
                workspace_path=action.workspace_path,
                target_path=action.target_path,
                content_sha256=action.content_sha256,
                original_sha256=action.original_sha256,
                argv=action.argv,
                timeout_seconds=action.timeout_seconds,
            )
            if current != action.action_fingerprint:
                raise ValueError(f"codex_action_fingerprint_mismatch:{action.action_id}")

    def _ensure_not_expired(self, contract: CodexGovernedContract) -> None:
        if datetime.fromisoformat(contract.expires_at) <= datetime.now(timezone.utc):
            raise ValueError("codex_contract_expired")

    def _required_contract(self, contract_id: str) -> CodexGovernedContract:
        contract = self.store.get(contract_id)
        if contract is None:
            raise FileNotFoundError(contract_id)
        return contract

    def _target_path(self, workspace_path: str, value: str) -> Path:
        workspace = Path(workspace_path).expanduser().resolve(strict=False)
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = workspace / candidate
        return resolve_within_root(candidate, workspace)

    def _filename_blocked(self, filename: str) -> bool:
        return any(
            fnmatch.fnmatch(filename.lower(), str(pattern).lower())
            for pattern in self._settings().get("blocked_filename_patterns", []) or []
        )

    def _settings(self) -> dict[str, Any]:
        settings = self.policy.get("codex_governed_execution", {})
        return settings if isinstance(settings, dict) else {}

    def _limit(self, name: str, default: int) -> int:
        return int(self._settings().get(name, default) or default)

    @staticmethod
    def _action_fingerprint(
        *,
        action_type: str,
        workspace_path: str,
        target_path: str | None,
        content_sha256: str | None,
        original_sha256: str | None,
        argv: list[str],
        timeout_seconds: int | None,
    ) -> str:
        payload = {
            "action_type": action_type,
            "workspace_path": str(
                Path(workspace_path).expanduser().resolve(strict=False)
            ),
            "target_path": target_path,
            "content_sha256": content_sha256,
            "original_sha256": original_sha256,
            "argv": argv,
            "timeout_seconds": timeout_seconds,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _contract_fingerprint(
        *,
        objective: str,
        workspace_path: str,
        action_fingerprints: list[str],
    ) -> str:
        payload = {
            "objective": objective,
            "workspace_path": str(
                Path(workspace_path).expanduser().resolve(strict=False)
            ),
            "action_fingerprints": action_fingerprints,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _safe_error_code(exc: Exception) -> str:
        text = str(exc).strip()
        return text if text and len(text) <= 240 else exc.__class__.__name__

    def _publish(
        self,
        event_type: str,
        summary: str,
        payload: dict[str, Any],
        *,
        status: str,
        severity: str = "info",
    ) -> None:
        contract_id = str(payload.get("contract_id") or "")
        contract = self.store.get(contract_id) if contract_id else None
        if contract and contract.run_id:
            run = self.codex_store.get_run(contract.run_id)
            if run is not None:
                try:
                    self.codex_store.add_event(
                        CodexRunEvent(
                            run_id=run.run_id,
                            session_id=run.session_id,
                            event_type=event_type,
                            status=status,
                            title="Codex governed execution",
                            human_message=summary,
                            technical_summary_sanitized=summary,
                            payload_sanitized=redact_payload(payload),
                            severity=severity,
                        )
                    )
                except OSError:
                    pass
        try:
            EventPublisherService().publish(
                EventPublishRequest(
                    event_type=event_type,
                    source_service="codex_governed_execution",
                    human_summary=summary,
                    payload=redact_payload(payload),
                    severity=severity,
                    status=status,
                    visibility="public",
                    copy_policy="copy_sanitized",
                )
            )
        except ValueError:
            return
