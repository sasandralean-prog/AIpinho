from __future__ import annotations

from typing import Any

from aipinho.schemas.agents.contracts import (
    AgentEventCreateRequest,
    AgentMessageCreateRequest,
    AgentRunCreateRequest,
    AgentSessionCreateRequest,
)
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.agents.hybrid_execution import (
    CanonicalPromptRequest,
    CodexDelegationRequest,
    CodexDiagnosticRequest,
    CodexModeDecision,
    CodexModeSelectRequest,
)
from aipinho.schemas.agents.ownership import WorkspaceLockCreateRequest, WriteConflictCheckRequest
from aipinho.services.agents.agent_delegation_service import AgentDelegationService
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.canonical_prompt_builder_service import CanonicalPromptBuilderService
from aipinho.services.agents.delegation_log_summary_service import DelegationLogSummaryService
from aipinho.services.agents.hybrid_execution_policy_service import HybridExecutionPolicyService
from aipinho.services.agents.workspace_lock_service import WorkspaceLockService
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService


class CodexHybridService:
    def __init__(
        self,
        *,
        kernel: AgentSessionKernelService | None = None,
        delegations: AgentDelegationService | None = None,
        locks: WorkspaceLockService | None = None,
        artifacts: ArtifactRuntimeService | None = None,
        policy: HybridExecutionPolicyService | None = None,
        prompt_builder: CanonicalPromptBuilderService | None = None,
        log_summary: DelegationLogSummaryService | None = None,
    ) -> None:
        self.kernel = kernel or AgentSessionKernelService()
        self.delegations = delegations or AgentDelegationService(kernel=self.kernel)
        self.locks = locks or WorkspaceLockService()
        self.artifacts = artifacts or ArtifactRuntimeService()
        self.policy = policy or HybridExecutionPolicyService()
        self.prompt_builder = prompt_builder or CanonicalPromptBuilderService()
        self.log_summary = log_summary or DelegationLogSummaryService()

    def select_mode(self, request: CodexModeSelectRequest) -> CodexModeDecision:
        policy = self.policy.codex()
        modes = policy["modes"]
        capabilities = set(request.available_capabilities)
        direct = set(policy.get("direct_capabilities", []))
        delegated = set(policy.get("delegated_capabilities", []))
        diagnostic = set(policy.get("diagnostic_capabilities", []))
        write = set(policy.get("write_capabilities", []))

        if request.requested_mode:
            selected = request.requested_mode
            reason_code = "explicit_mode_selected"
        elif request.risk_level in set(policy.get("high_risk_levels", [])):
            selected = "codex_observe_only"
            reason_code = "high_risk_requires_explicit_mode"
        elif capabilities & direct and capabilities & diagnostic:
            selected = "codex_hybrid_supervisor"
            reason_code = "diagnostics_and_direct_change_required"
        elif capabilities & direct:
            selected = "codex_direct_executor"
            reason_code = "direct_technical_capability_required"
        elif capabilities & delegated:
            selected = "codex_delegated_to_aipinho"
            reason_code = "local_repeatable_capability_delegated"
        else:
            selected = "codex_observe_only"
            reason_code = "no_execution_capability_requested"

        conflicts = self._conflicting_locks(request.workspace, request.active_locks)
        if selected in {"codex_direct_executor", "codex_hybrid_supervisor"} and conflicts:
            selected = "codex_observe_only"
            reason_code = "workspace_locked_by_other_agent"
        mode = modes[selected]
        return CodexModeDecision(
            selected_mode=selected,
            reason=reason_code.replace("_", " "),
            reason_code=reason_code,
            expected_owner_agent=str(mode["owner_agent"]),
            requires_lock=bool(request.workspace and capabilities & write and selected in {"codex_direct_executor", "codex_hybrid_supervisor"}),
            allowed_actions=list(mode.get("allowed_actions", [])),
            conflicting_lock_ids=conflicts,
        )

    def delegate_to_aipinho(self, request: CodexDelegationRequest) -> dict[str, Any]:
        session = self._session(request.session_id, request.workspace)
        parent_run = self.kernel.create_run(
            "codex",
            session.session_id,
            AgentRunCreateRequest(
                operation_type="codex_delegated_to_aipinho",
                status="running",
                workspace_id=request.workspace,
                capabilities_requested=request.requested_capabilities,
                metadata_sanitized={"execution_mode": "governed_autorun", "source_mode": "codex_delegated_to_aipinho"},
            ),
        )
        self.kernel.add_message(
            "codex",
            session.session_id,
            AgentMessageCreateRequest(role="user", content_sanitized=request.user_prompt, run_id=parent_run.run_id),
        )
        canonical = self.prompt_builder.build(
            CanonicalPromptRequest(
                user_message=request.user_prompt,
                source_agent="codex",
                workspace=request.workspace,
                intent=request.requested_operation,
                constraints=request.constraints,
                desired_outputs=request.expected_outputs,
                validation_required=True,
                risk_level=request.risk_level,
            )
        )
        response = self.delegations.create_delegation(
            "codex",
            parent_run.run_id,
            DelegationCreateRequest(
                target_agent_id="aipinho",
                user_goal=canonical.canonical_prompt,
                requested_operation=request.requested_operation,
                operation_type=request.requested_operation,
                workspace_id=request.workspace,
                capabilities_requested=request.requested_capabilities,
                constraints={**request.constraints, "canonical_prompt": True, "truth_contract": "evidence_before_success"},
                expected_outputs=request.expected_outputs,
                risk_level=request.risk_level,
                execution_mode="governed_autorun",
                metadata_sanitized={"source_mode": "codex_delegated_to_aipinho", "canonical_prompt": True},
            ),
        )
        lock = self._lock_delegated_write(response, request)
        self.kernel.add_event(
            parent_run.run_id,
            AgentEventCreateRequest(
                event_type="codex_delegated_to_aipinho",
                status=response.status,
                human_message="Codex delegou a execucao local para a AIpinho.",
                delegation_id=response.delegation.delegation_id,
                payload_sanitized={
                    "bridge_task_id": response.delegation.delegation_id,
                    "child_run_id": response.delegation.child_run_id,
                    "workspace_lock_id": lock.lock_id if lock else None,
                },
            ),
        )
        return self.delegation_details(response.delegation.delegation_id)

    def collect_diagnostics(self, request: CodexDiagnosticRequest) -> dict[str, Any]:
        payload = request.model_copy(
            update={
                "requested_capabilities": sorted(set(request.requested_capabilities) | {"read_workspace", "validation"}),
                "constraints": {**request.constraints, "read_only": True, "max_summary_items": request.max_summary_items},
                "expected_outputs": ["diagnostic_summary", "event_trace", "full_log_artifact"],
            }
        )
        return self.delegate_to_aipinho(CodexDelegationRequest(**payload.model_dump(exclude={"max_summary_items"})))

    def delegation_details(self, delegation_id: str) -> dict[str, Any]:
        response = self.delegations.get_delegation(delegation_id)
        item = response.delegation
        events = self.kernel.list_run_events(item.parent_run_id, include_hidden=False, limit=200)
        if item.child_run_id:
            events.extend(self.kernel.list_run_events(item.child_run_id, include_hidden=False, limit=200))
        artifacts = self.artifacts.by_bridge_task(delegation_id, limit=100)
        limit = int(self.policy.log_summary().get("default_max_items", 5))
        summary = self.log_summary.summarize(status=response.status, events=events, artifacts=artifacts, max_items=limit)
        return {
            "status": response.status,
            "bridge_task_id": delegation_id,
            "aipinho_task_id": item.child_run_id,
            "delegation": item.model_dump(),
            "events": [event.model_dump() for event in events],
            "artifacts": artifacts,
            "final_answer": response.result.summary if response.result and response.result.status in {"completed", "completed_with_warnings"} else None,
            "result": response.result.model_dump() if response.result else None,
            "log_summary": summary.model_dump(),
            "raw_default_visible": False,
        }

    def _session(self, session_id: str | None, workspace: str | None):
        if session_id:
            existing = self.kernel.get_session("codex", session_id, include_compat=False)
            if existing is not None:
                return existing
        return self.kernel.create_session(
            "codex",
            AgentSessionCreateRequest(
                title="Codex hybrid delegation",
                active_workspace_id=workspace,
                metadata_sanitized={"source_mode": "codex_hybrid"},
            ),
        )

    def _conflicting_locks(self, workspace: str | None, supplied: list[dict[str, Any]]) -> list[str]:
        conflicts = [str(item.get("lock_id")) for item in supplied if item.get("owner_agent") not in {None, "codex", "codex_agent"} and item.get("status", "active") == "active"]
        if workspace:
            decision = self.locks.check_write_conflict(
                WriteConflictCheckRequest(workspace=workspace, actor_agent="codex", target_paths=[workspace])
            )
            conflicts.extend(lock.lock_id for lock in decision.conflicting_locks)
        return sorted(set(conflicts))

    def _lock_delegated_write(self, response, request: CodexDelegationRequest):
        write = set(self.policy.codex().get("write_capabilities", []))
        if response.status != "running" or not request.workspace or not (set(request.requested_capabilities) & write):
            return None
        return self.locks.create(
            WorkspaceLockCreateRequest(
                workspace=request.workspace,
                owner_agent="aipinho",
                owner_task_id=response.delegation.child_run_id,
                bridge_task_id=response.delegation.delegation_id,
                reason="delegated_write_ownership",
            )
        )
