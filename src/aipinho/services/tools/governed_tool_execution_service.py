from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.governance.lifecycle import (
    CanonicalOperationContract,
    CanonicalPermission,
    CanonicalPolicyFacet,
)
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.policy_kernel.remote_repository_scope_service import RemoteRepositoryScopeService
from aipinho.services.policy_kernel.mission_staging_policy_service import MissionStagingPolicyService
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.session.session_store import utc_now
from aipinho.services.tools.execution_audit_service import ExecutionAuditService
from aipinho.services.tools.shell_command_policy_service import ShellCommandPolicyService
from aipinho.services.tools.tool_registry_service import ToolRegistryService
from aipinho.services.tools.write_capability_envelope_service import WriteCapabilityEnvelopeService
from aipinho.utils.yaml_loader import load_yaml_file


class GovernedToolExecutionService:
    def __init__(
        self,
        registry: ToolRegistryService | None = None,
        approvals: ApprovalService | None = None,
        audit: ExecutionAuditService | None = None,
        policy_path: Path | None = None,
        runner=subprocess.run,
        opener=urlopen,
        shell_policy: ShellCommandPolicyService | None = None,
        write_envelopes: WriteCapabilityEnvelopeService | None = None,
        task_runs: TaskRunStore | None = None,
        authority_grants: AuthorityGrantService | None = None,
        effective_policy: EffectivePolicyDecisionService | None = None,
        workspace_roles: WorkspaceRoleContractService | None = None,
        permission_matrix: WorkspacePermissionMatrixService | None = None,
        staging_policy: MissionStagingPolicyService | None = None,
        remote_scopes: RemoteRepositoryScopeService | None = None,
    ) -> None:
        self.registry = registry or ToolRegistryService().load()
        self.approvals = approvals or ApprovalService()
        self.audit = audit or ExecutionAuditService()
        self.policy_path = policy_path or PATHS.config_root / "policies" / "governed_tool_execution_policy.yaml"
        self.policy = load_yaml_file(self.policy_path, critical=True, root=self.policy_path.parent)
        self.runner = runner
        self.opener = opener
        self.shell_policy = shell_policy or ShellCommandPolicyService(policy_path=self.policy_path)
        self.effective_policy = effective_policy or EffectivePolicyDecisionService()
        self.workspace_roles = workspace_roles or WorkspaceRoleContractService().load()
        self.permission_matrix = permission_matrix or WorkspacePermissionMatrixService().load()
        self.staging_policy = staging_policy or MissionStagingPolicyService()
        self.write_envelopes = write_envelopes or WriteCapabilityEnvelopeService(
            workspace_roles=self.workspace_roles,
            effective_policy=self.effective_policy,
        )
        self.task_runs = task_runs or TaskRunStore()
        self.authority_grants = authority_grants or AuthorityGrantService()
        self.missions = MissionContractService(staging_policy=self.staging_policy)
        self.remote_scopes = remote_scopes or RemoteRepositoryScopeService(policy_path=self.policy_path)

    def request_approval(self, request: ToolExecutionRequest) -> dict[str, object]:
        decision = self._decision(request)
        canonical = decision.get("canonical_policy")
        if canonical is None or self._canonical_hard_blocked(canonical):
            result = self._result_from_decision(request, decision)
            self.audit.record(result)
            return {"status": result.status, "result": result}
        if canonical.permission == CanonicalPermission.ALLOWED:
            return {
                "status": "authorized",
                "approval": None,
                "tool_execution_request_id": request.tool_execution_request_id,
                "request_fingerprint": self._request_fingerprint(request),
                "safe_to_execute_after_approval": True,
                "canonical_policy": canonical,
            }

        tool = decision["tool"]
        assert isinstance(tool, ToolDefinition)
        now = datetime.now(timezone.utc)
        snapshot = self._policy_snapshot(request, tool, decision)
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=request.preview_id or request.tool_execution_request_id,
            draft_id=request.draft_id or request.tool_execution_request_id,
            session_id=request.session_id,
            status="pending",
            actions_requested=[tool.action],
            approval_scope="future_execution",
            reason=f"Governed tool execution requested for {tool.tool_id}.",
            risk_level=tool.risk_level,
            policy_snapshot=snapshot,
            expires_at=(now + timedelta(minutes=self.approvals.policy.ttl_minutes())).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=request.requested_by or Actor(type="user", id="local_user"),
            trace=[{
                "stage": "governed_tool_approval",
                "decision": "pending",
                "reason": "approval_required_before_execution",
                "tool_id": tool.tool_id,
                "action": tool.action,
            }],
            execution_status="not_executed",
        )
        self.approvals.store.save(approval)
        self.approvals.append_event(
            approval.approval_id,
            "approval_created",
            "ApprovalRequest criado para execucao governada de tool; nada foi executado.",
            data={"tool_id": tool.tool_id, "action": tool.action},
        )
        return {
            "status": "approval_required",
            "approval": approval,
            "tool_execution_request_id": request.tool_execution_request_id,
            "request_fingerprint": self._request_fingerprint(request),
            "safe_to_execute_after_approval": True,
            "canonical_policy": canonical,
        }

    def preview_decision(self, request: ToolExecutionRequest) -> dict[str, Any]:
        decision = self._decision(request)
        tool = decision.get("tool")
        canonical = decision.get("canonical_policy")
        return {
            "allowed": bool(canonical is not None and canonical.permission == CanonicalPermission.ALLOWED),
            "tool_id": tool.tool_id if isinstance(tool, ToolDefinition) else request.tool_id,
            "action": tool.action if isinstance(tool, ToolDefinition) else None,
            "capability": decision.get("canonical_capability") or (tool.capability if isinstance(tool, ToolDefinition) else None),
            "violations": list(decision.get("violations", [])),
            "warnings": list(decision.get("warnings", [])),
            "trace": list(decision.get("trace", [])),
            "shell_classification": (
                decision["shell_classification"].model_dump()
                if hasattr(decision.get("shell_classification"), "model_dump")
                else None
            ),
            "canonical_policy": (
                canonical.model_dump(mode="json") if canonical is not None else None
            ),
        }

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        execution_id = f"exec_{uuid4().hex}"
        decision = self._decision(request)
        canonical = decision.get("canonical_policy")
        if canonical is None or self._canonical_hard_blocked(canonical):
            result = self._result_from_decision(request, decision, execution_id=execution_id)
            self.audit.record(result)
            return result
        if canonical.permission == CanonicalPermission.ASK:
            if request.approval_id:
                decision["violations"].append("approval_not_effective")
            else:
                decision["violations"].append("approval_id_required")
            result = self._result_from_decision(request, decision, execution_id=execution_id)
            self.audit.record(result)
            return result

        classification = decision.get("shell_classification")
        git_classification = getattr(classification, "git_classification", None)
        if git_classification is not None and git_classification.safe_for_governed_execution and git_classification.operation_class != "local_read":
            observation = self._observe_git_runtime(request, git_classification)
            decision = self._decision(request, git_observation=observation)
            canonical = decision.get("canonical_policy")
            if canonical is None or self._canonical_hard_blocked(canonical) or canonical.permission == CanonicalPermission.ASK:
                if canonical is not None and canonical.permission == CanonicalPermission.ASK:
                    decision["violations"].append("approval_id_required")
                result = self._result_from_decision(request, decision, execution_id=execution_id)
                self.audit.record(result)
                return result

        tool = decision["tool"]
        assert isinstance(tool, ToolDefinition)
        if tool.adapter == "shell" and tool.action == "run_command":
            preflight_error = self._shell_execution_preflight_error(request)
            if preflight_error:
                decision["violations"].append(preflight_error)
                result = self._result_from_decision(request, decision, execution_id=execution_id)
                self.audit.record(result)
                return result

        if decision.get("uses_mission_authority"):
            authority_error = self._consume_mission_authority(request, decision)
            if authority_error:
                decision["violations"].append(authority_error)
                result = self._result_from_decision(request, decision, execution_id=execution_id)
                self.audit.record(result)
                return result

        timeout = self._timeout_seconds(request)
        if tool.adapter == "shell" and tool.action == "run_command":
            result = self._execute_shell(request, tool, decision, execution_id=execution_id, timeout=timeout)
            if git_classification is not None and result.status == "executed_governed":
                if git_classification.operation == "git_push":
                    result = self._post_validate_git_push(request, decision, result)
                elif git_classification.operation == "git_clone":
                    result = self._post_validate_git_clone(request, decision, result)
        elif tool.adapter == "filesystem" and tool.action == "create_directory":
            result = self._execute_create_directory(request, tool, decision, execution_id=execution_id)
        elif tool.adapter == "web" and tool.action == "web_request":
            result = self._execute_web(request, tool, decision, execution_id=execution_id, timeout=timeout)
        else:
            decision["violations"].append("governed_adapter_not_implemented")
            result = self._result_from_decision(request, decision, execution_id=execution_id)
        self.audit.record(result)
        return result

    def _decision(self, request: ToolExecutionRequest, *, git_observation: dict[str, str] | None = None) -> dict[str, Any]:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        tool = self.registry.get_tool(request.tool_id)
        violations: list[str] = []
        warnings: list[str] = []
        trace: list[dict[str, Any]] = []
        task_run = None
        if request.task_run_id:
            task_run = self.task_runs.get_run(request.task_run_id)
            if task_run is None:
                violations.append("canonical_task_run_not_found")
            elif task_run.mission_contract is None or not self.missions.verify(task_run.mission_contract):
                violations.append("canonical_task_run_mission_contract_invalid")

        global_errors: list[str] = []
        if not config.get("enabled", False):
            global_errors.append("governed_tool_execution_disabled")
        if request.mode != "governed":
            global_errors.append("mode_not_governed")
        if tool is None:
            global_errors.append("unknown_tool")
            violations.extend(global_errors)
            return {
                "allowed": False,
                "tool": None,
                "violations": list(dict.fromkeys(violations)),
                "warnings": warnings,
                "trace": trace,
                "canonical_policy": None,
            }
        if not tool.enabled:
            global_errors.append("disabled_tool")
        if not tool.execute_supported:
            global_errors.append("execute_not_supported")
        if not tool.requires_approval:
            global_errors.append("approval_required_for_governed_execution")
        if tool.action not in set(config.get("allowed_actions", []) or []):
            global_errors.append("action_not_allowed_for_governed_execution")
        if tool.action in set(config.get("denied_actions", []) or []):
            global_errors.append("action_denied_for_governed_execution")
        if tool.capability not in set(config.get("allowed_capabilities", []) or []):
            global_errors.append("capability_not_allowed_for_governed_execution")
        if tool.capability in set(config.get("denied_capabilities", []) or []):
            global_errors.append("capability_denied_for_governed_execution")
        violations.extend(global_errors)

        workspace = str(request.input.get("workspace") or "")
        local_resources = (
            list(task_run.mission_contract.local_resources)
            if task_run is not None and task_run.mission_contract is not None
            else []
        )
        role_decision = None
        workspace_error = None
        if tool.action in set(config.get("workspace_required_for", []) or []):
            workspace_error, role_decision = self._workspace_error(
                workspace,
                local_resources=local_resources,
                mission_bound=task_run is not None,
            )
            if workspace_error:
                violations.append(workspace_error)

        shell_decision = None
        if tool.adapter == "shell" and tool.action == "run_command":
            shell_decision = self._shell_decision(request)
            trace.extend(shell_decision["trace"])
            warnings.extend(shell_decision["warnings"])
            violations.extend(shell_decision["violations"])

        capability = self._canonical_capability(tool, shell_decision)
        resource_id = (
            role_decision.contract.workspace_id
            if role_decision is not None and role_decision.contract is not None
            else None
        )
        git_classification = (
            getattr(shell_decision.get("classification"), "git_classification", None)
            if shell_decision is not None else None
        )
        git_scope_decision = None
        git_repository_identity = None
        git_branch = None
        git_scope_resource_id = None
        if git_classification is not None and git_classification.requires_remote_scope:
            git_scope_decision = self._git_scope_decision(
                task_run=task_run, request=request, git_classification=git_classification,
                git_observation=git_observation,
            )
            if git_scope_decision is not None:
                git_repository_identity = git_scope_decision.repository_identity
                git_branch = git_scope_decision.branch
                git_scope_resource_id = git_scope_decision.resource_id

        filesystem_permission = None
        staging_materialization = False
        if tool.adapter == "filesystem" and tool.action == "create_directory":
            target_path = str(request.input.get("path") or workspace or "")
            filesystem_permission = self.permission_matrix.decide_with_resources(
                path=target_path,
                permission="create_directory",
                local_resources=local_resources,
            )
            staging_materialization = self._staging_materialization_allowed(
                task_run=task_run,
                resource_id=filesystem_permission.workspace_id,
            )

        approval_valid = False
        approval_error = None
        if request.approval_id:
            approval_error = self._approval_error(request, {"tool": tool})
            approval_valid = approval_error is None
        authority_resource_id = git_scope_resource_id or resource_id
        mission_authority = self._mission_authority_decision(
            task_run,
            capability=capability,
            workspace=workspace or None,
            resource_id=authority_resource_id,
            repository_identity=git_repository_identity,
            branch=git_branch,
            consume=False,
        )
        mission_authority_ready = bool(
            mission_authority is not None
            and mission_authority.reason_code == "grant_effective"
        )
        human_authority_effective = approval_valid or mission_authority_ready

        facets: list[CanonicalPolicyFacet] = [
            CanonicalPolicyFacet(
                facet="capability_demand",
                permission=CanonicalPermission.ALLOWED,
                source="governed_tool_execution",
                reason_code="capability_requested",
                capability=capability,
                resource_id=resource_id,
            ),
            CanonicalPolicyFacet(
                facet="governed_tool_policy",
                permission=(CanonicalPermission.DENIED if global_errors else CanonicalPermission.ALLOWED),
                source="governed_tool_execution_policy",
                reason_code=(global_errors[0] if global_errors else "governed_tool_policy_allowed"),
                capability=capability,
                resource_id=resource_id,
                details={"violations": global_errors},
            ),
        ]
        if tool.action in set(config.get("workspace_required_for", []) or []):
            facets.append(
                CanonicalPolicyFacet(
                    facet="workspace_resolution",
                    permission=(CanonicalPermission.DENIED if workspace_error else CanonicalPermission.ALLOWED),
                    source="workspace_role_contract",
                    reason_code=workspace_error or "workspace_allowed",
                    capability=capability,
                    resource_id=resource_id,
                )
            )

        if filesystem_permission is not None:
            permission = (
                CanonicalPermission.DENIED
                if filesystem_permission.status == "denied"
                else CanonicalPermission.ALLOWED
                if staging_materialization or filesystem_permission.status == "allowed"
                else CanonicalPermission.ASK
            )
            reason = (
                "mission_staging_materialization_permission_derived"
                if staging_materialization and permission == CanonicalPermission.ALLOWED
                else filesystem_permission.reason_code
            )
            facets.append(
                CanonicalPolicyFacet(
                    facet="resource_permission",
                    permission=permission,
                    source="workspace_permission_matrix",
                    reason_code=str(reason),
                    capability=capability,
                    resource_id=filesystem_permission.workspace_id,
                    requires_human_authority=(permission == CanonicalPermission.ASK),
                    details={"workspace_role": filesystem_permission.workspace_role},
                    trace=list(filesystem_permission.trace),
                )
            )

        if git_classification is not None and git_classification.requires_remote_scope:
            if git_observation is not None and git_observation.get("error"):
                remote_permission = CanonicalPermission.DENIED
                remote_reason = str(git_observation["error"])
            elif git_scope_decision is None:
                remote_permission = CanonicalPermission.DENIED
                remote_reason = "git_remote_scope_unresolved"
            else:
                remote_permission = (
                    CanonicalPermission.ALLOWED
                    if git_scope_decision.status == "allowed"
                    else CanonicalPermission.NEEDS_CLARIFICATION
                    if git_scope_decision.status == "needs_clarification"
                    else CanonicalPermission.DENIED
                )
                remote_reason = str(git_scope_decision.reason_code)
            facets.append(
                CanonicalPolicyFacet(
                    facet="remote_repository_scope",
                    permission=remote_permission,
                    source="remote_repository_scope",
                    reason_code=remote_reason,
                    capability=capability,
                    resource_id=git_scope_resource_id,
                    details={
                        "repository_identity": git_repository_identity,
                        "branch": git_branch,
                        "git_operation": git_classification.operation,
                    },
                )
            )

        if shell_decision is not None:
            classification = shell_decision["classification"]
            shell_permission = (
                CanonicalPermission.DENIED
                if classification.policy_decision == "blocked"
                else CanonicalPermission.ASK
                if classification.policy_decision == "approval_required"
                else CanonicalPermission.ALLOWED
            )
            facets.append(
                CanonicalPolicyFacet(
                    facet="shell_policy",
                    permission=shell_permission,
                    source="shell_command_policy",
                    reason_code=f"shell_category:{classification.category}",
                    capability=capability,
                    resource_id=resource_id,
                    requires_human_authority=(shell_permission == CanonicalPermission.ASK),
                    details={"category": classification.category},
                    trace=list(classification.trace),
                )
            )
            if classification.category in {"git_write_shell", "network_shell"}:
                facets.append(
                    CanonicalPolicyFacet(
                        facet="global_policy",
                        permission=CanonicalPermission.DENIED,
                        source="m5_ambiguous_external_shell_boundary",
                        reason_code=(
                            "git_write_requires_granular_classification"
                            if classification.category == "git_write_shell"
                            else "network_shell_requires_granular_classification"
                        ),
                        capability=capability,
                        resource_id=resource_id,
                        details={"shell_category": classification.category},
                    )
                )

            operation_type = shell_decision.get("operation_type")
            if operation_type:
                envelope_decision = self.write_envelopes.create(
                    task_id=request.task_run_id or request.draft_id or request.tool_execution_request_id,
                    session_id=request.session_id,
                    workspace_path=workspace,
                    target_path=workspace,
                    operation_type=operation_type,
                    preview_id=request.preview_id,
                    approval_id=(request.approval_id if approval_valid else None),
                    expected_side_effects=classification.expected_side_effects,
                    risk_score=classification.risk_score,
                    actor="governed_tool_execution",
                    local_resources=local_resources,
                    human_authority_effective=mission_authority_ready,
                )
                shell_decision["envelope_decision"] = envelope_decision
                facets.extend(envelope_decision.canonical_policy_decision.facets if envelope_decision.canonical_policy_decision else [])
                if envelope_decision.canonical_policy_decision is not None:
                    if envelope_decision.canonical_policy_decision.permission == CanonicalPermission.DENIED:
                        violations.extend(envelope_decision.envelope.blocking_reasons)

        if not staging_materialization:
            facets.append(
                CanonicalPolicyFacet(
                    facet="tool_human_authority_requirement",
                    permission=CanonicalPermission.ASK,
                    source="governed_tool_execution_policy",
                    reason_code="approval_required_before_execution",
                    capability=capability,
                    resource_id=resource_id,
                    requires_human_authority=True,
                )
            )
        else:
            facets.append(
                CanonicalPolicyFacet(
                    facet="derived_resource_materialization",
                    permission=CanonicalPermission.ALLOWED,
                    source="mission_staging_policy",
                    reason_code="mission_staging_materialization_authorized",
                    capability=capability,
                    resource_id=resource_id,
                    details={"authority_inherited": False},
                )
            )
        if approval_valid:
            facets.append(
                CanonicalPolicyFacet(
                    facet="human_authority",
                    permission=CanonicalPermission.ALLOWED,
                    source="approved_execution_binding",
                    reason_code="approval_binding_valid",
                    capability=capability,
                    resource_id=resource_id,
                )
            )
        elif request.approval_id and approval_error:
            facets.append(
                CanonicalPolicyFacet(
                    facet="human_authority",
                    permission=CanonicalPermission.DENIED,
                    source="approval_service",
                    reason_code=approval_error,
                    capability=capability,
                    resource_id=resource_id,
                )
            )
        if mission_authority_ready:
            facets.append(
                CanonicalPolicyFacet(
                    facet="human_authority",
                    permission=CanonicalPermission.ALLOWED,
                    source="mission_authority_grant",
                    reason_code="grant_effective",
                    capability=capability,
                    resource_id=resource_id,
                )
            )

        contract = CanonicalOperationContract(
            session_id=request.session_id,
            source_channel="governed_tool_execution",
            intent_type=str(tool.action),
            operation_type=str(tool.action),
            contract_type="governed_tool_execution",
            runtime_profile="governed_tool_execution",
            requires_task=task_run is not None,
            workspace_mutation=bool(tool.side_effect and tool.adapter != "web"),
            requested_actions=[tool.action],
            workspace_path=workspace or None,
            risk_level=str(tool.risk_level or "low"),
        )
        canonical = self.effective_policy.resolve_facets(
            contract,
            facets=facets,
            capability=capability,
            resource_id=resource_id,
        )
        trace.extend(canonical.trace)
        trace.append({
            "stage": "governed_tool_policy",
            "decision": canonical.permission.value,
            "action": tool.action,
            "capability": capability,
            "requires_approval": canonical.requires_approval,
        })
        if canonical.permission == CanonicalPermission.DENIED and not violations:
            blocking = next(
                (item for item in canonical.facets if item.permission == CanonicalPermission.DENIED),
                None,
            )
            if blocking is not None and blocking.reason_code:
                violations.append(str(blocking.reason_code))
        return {
            "allowed": canonical.permission in {CanonicalPermission.ALLOWED, CanonicalPermission.ASK},
            "tool": tool,
            "violations": list(dict.fromkeys(violations)),
            "warnings": list(dict.fromkeys(warnings)),
            "trace": trace,
            "shell_classification": shell_decision.get("classification") if shell_decision else None,
            "write_envelope": shell_decision.get("envelope_decision").envelope if shell_decision and shell_decision.get("envelope_decision") else None,
            "canonical_policy": canonical,
            "canonical_capability": capability,
            "resource_id": resource_id,
            "authority_resource_id": authority_resource_id,
            "git_scope_decision": git_scope_decision,
            "git_repository_identity": git_repository_identity,
            "git_branch": git_branch,
            "task_run": task_run,
            "mission_authority_ready": mission_authority_ready,
            "approval_valid": approval_valid,
            "uses_mission_authority": mission_authority_ready and not approval_valid,
        }

    def _staging_materialization_allowed(self, *, task_run, resource_id: str | None) -> bool:
        if (
            task_run is None
            or task_run.mission_contract is None
            or not task_run.parent_task_id
            or not resource_id
        ):
            return False
        resource = next(
            (item for item in task_run.mission_contract.local_resources if item.resource_id == resource_id),
            None,
        )
        parent_run = self.task_runs.get_run_by_task_id(task_run.parent_task_id)
        if (
            resource is None
            or resource.resource_type != "mission_staging"
            or parent_run is None
            or parent_run.mission_contract is None
        ):
            return False
        try:
            self.missions.validate_child_contract(
                parent=parent_run.mission_contract,
                child=task_run.mission_contract,
            )
            self.staging_policy.validate_derived_resource(
                parent=parent_run.mission_contract,
                resource=resource,
            )
        except ValueError:
            return False
        return True

    def _shell_decision(self, request: ToolExecutionRequest) -> dict[str, Any]:
        workspace = str(request.input.get("workspace") or "")
        argv = request.input.get("argv")
        command = str(request.input.get("command") or "")
        normalized_argv = [str(item) for item in argv] if isinstance(argv, list) else None
        classification = self.shell_policy.classify(
            argv=normalized_argv,
            command=command,
            working_dir=workspace,
        )
        violations: list[str] = []
        warnings: list[str] = []
        if classification.policy_decision == "blocked":
            violations.append(f"shell_category_blocked:{classification.category}")
        elif classification.policy_decision == "approval_required":
            warnings.append(f"shell_category_requires_approval:{classification.category}")
        trace = [{
            "stage": "shell_policy",
            "decision": classification.policy_decision,
            "command_id": classification.command_id,
            "category": classification.category,
            "risk_score": classification.risk_score,
            "expected_side_effects": classification.expected_side_effects,
        }]
        return {
            "classification": classification,
            "operation_type": self._operation_type_for_shell_category(classification.category),
            "envelope_decision": None,
            "violations": violations,
            "warnings": warnings,
            "trace": trace,
        }

    @staticmethod
    def _operation_type_for_shell_category(category: str) -> str | None:
        return {
            "readonly_shell": "run_shell_readonly",
            "git_read_shell": "run_shell_readonly",
            "test_shell": "run_shell_test",
            "build_shell": "run_shell_build",
            "package_shell": "run_shell_build",
            "write_shell": "run_shell_write",
        }.get(category)

    @staticmethod
    def _canonical_capability(tool: ToolDefinition, shell_decision: dict[str, Any] | None) -> str:
        if tool.adapter == "filesystem" and tool.action == "create_directory":
            return "create_directory"
        if shell_decision is not None:
            classification = shell_decision["classification"]
            git_classification = getattr(classification, "git_classification", None)
            if git_classification is not None:
                return str(git_classification.capability)
            category = str(classification.category)
            return {
                "readonly_shell": "shell_readonly",
                "git_read_shell": "shell_readonly",
                "test_shell": "shell_test",
                "build_shell": "shell_build",
                "package_shell": "shell_build",
                "write_shell": "script_execution",
                "process_control_shell": "script_execution",
                "network_shell": "network_download",
                "git_write_shell": "git_write_ambiguous",
                "unknown_shell": "script_execution",
            }.get(category, str(tool.capability))
        if tool.adapter == "web" and tool.action == "web_request":
            return "network_download"
        return str(tool.capability)

    def _git_scope_decision(
        self,
        *,
        task_run,
        request: ToolExecutionRequest,
        git_classification,
        git_observation: dict[str, str] | None,
    ):
        if task_run is None or task_run.mission_contract is None:
            return None
        resources = list(task_run.mission_contract.remote_resources)
        candidates = [
            item for item in resources
            if item.role != "remote_denied"
            and git_classification.operation in set(item.permissions)
        ]
        repository_locator = str(request.input.get("repository_locator") or "").strip() or None
        if repository_locator is None and len(candidates) == 1:
            repository_locator = candidates[0].locator
        if repository_locator is None:
            return None
        branch = str(request.input.get("branch") or "").strip() or git_classification.branch
        if git_observation and git_classification.operation in {"git_commit", "git_push"}:
            branch = git_observation.get("current_branch") or branch
        if not branch and len(candidates) == 1 and len(candidates[0].allowed_branches) == 1:
            branch = candidates[0].allowed_branches[0]
        observed = git_observation.get("remote_locator") if git_observation else None
        return self.remote_scopes.decide(
            remote_resources=resources,
            repository_locator=repository_locator,
            branch=branch,
            operation=git_classification.operation,
            observed_repository_locator=observed,
            require_promotion_reobservation=git_observation is not None,
        )

    def _observe_git_runtime(self, request: ToolExecutionRequest, git_classification) -> dict[str, str]:
        workspace = str(request.input.get("workspace") or "")
        observation: dict[str, str] = {}
        remote_name = str(git_classification.remote_name or "origin")
        if git_classification.requires_remote_scope:
            if self._is_remote_locator(remote_name):
                observation["remote_locator"] = remote_name
            else:
                completed = self._run_git_read(workspace, ["git", "remote", "get-url", remote_name])
                if completed.returncode != 0 or not str(completed.stdout or "").strip():
                    return {"error": "git_remote_reobservation_failed"}
                observation["remote_locator"] = str(completed.stdout).strip()
        if git_classification.operation in {"git_commit", "git_push"}:
            completed = self._run_git_read(workspace, ["git", "branch", "--show-current"])
            branch = str(completed.stdout or "").strip()
            if completed.returncode != 0 or not branch:
                return {"error": "git_branch_reobservation_failed"}
            observation["current_branch"] = branch
            if git_classification.operation == "git_push" and git_classification.branch and branch != git_classification.branch:
                return {"error": "git_push_current_branch_mismatch", "current_branch": branch}
        return observation

    def _run_git_read(self, workspace: str, argv: list[str]):
        return self.runner(
            argv, cwd=workspace, timeout=self._timeout_seconds_from_policy(),
            capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False,
        )

    def _timeout_seconds_from_policy(self) -> int:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        return int(config.get("default_timeout_seconds", 30) or 30)

    def _is_remote_locator(self, value: str) -> bool:
        try:
            self.remote_scopes.identities.normalize(value)
        except ValueError:
            return False
        return True

    def _mission_authority_decision(
        self,
        task_run,
        *,
        capability: str,
        workspace: str | None,
        resource_id: str | None,
        repository_identity: str | None = None,
        branch: str | None = None,
        consume: bool,
    ):
        if task_run is None or task_run.mission_contract is None:
            return None
        return self.authority_grants.decision_for_contract(
            task_run.mission_contract,
            action=capability,
            path=workspace,
            resource_id=resource_id,
            repository_identity=repository_identity,
            branch=branch,
            consume=consume,
        )

    def _consume_mission_authority(
        self,
        request: ToolExecutionRequest,
        decision: dict[str, Any],
    ) -> str | None:
        consumed = self._mission_authority_decision(
            decision.get("task_run"),
            capability=str(decision.get("canonical_capability") or ""),
            workspace=str(request.input.get("workspace") or "") or None,
            resource_id=decision.get("authority_resource_id") or decision.get("resource_id"),
            repository_identity=decision.get("git_repository_identity"),
            branch=decision.get("git_branch"),
            consume=True,
        )
        if consumed is None:
            return "mission_authority_missing"
        if consumed.reason_code != "grant_consumed":
            return consumed.reason_code
        return None

    @staticmethod
    def _canonical_hard_blocked(canonical) -> bool:
        return canonical.permission in {
            CanonicalPermission.DENIED,
            CanonicalPermission.NEEDS_CLARIFICATION,
            CanonicalPermission.INVALID,
            CanonicalPermission.EXPIRED,
            CanonicalPermission.STALE,
        }

    def _approval_error(self, request: ToolExecutionRequest, decision: dict[str, Any]) -> str | None:
        if not request.approval_id:
            return "approval_id_required"
        approval = self.approvals.get_approval(request.approval_id)
        if approval is None:
            return "approval_not_found"
        if approval.status != "approved":
            return f"approval_not_approved:{approval.status}"
        tool = decision["tool"]
        assert isinstance(tool, ToolDefinition)
        if tool.action not in approval.actions_requested:
            return "approval_action_mismatch"
        approved_hash = str(approval.policy_snapshot.config_versions.get("tool_execution_request_hash") or "")
        if approved_hash and approved_hash != self._request_fingerprint(request):
            return "approval_request_fingerprint_mismatch"
        return None

    def _shell_execution_preflight_error(self, request: ToolExecutionRequest) -> str | None:
        argv, parse_error = self._command_argv(request.input)
        if parse_error:
            return parse_error
        return self._executable_error(argv)

    def _execute_create_directory(
        self,
        request: ToolExecutionRequest,
        tool: ToolDefinition,
        decision: dict[str, Any],
        *,
        execution_id: str,
    ) -> ToolExecutionResult:
        workspace = Path(str(request.input.get("workspace") or "")).expanduser().resolve(strict=False)
        target = Path(str(request.input.get("path") or workspace)).expanduser().resolve(strict=False)
        try:
            target.relative_to(workspace)
        except ValueError:
            decision["violations"].append("target_outside_workspace")
            return self._result_from_decision(request, decision, execution_id=execution_id)
        existed = target.exists()
        target.mkdir(parents=True, exist_ok=True)
        return ToolExecutionResult(
            execution_id=execution_id,
            tool_id=request.tool_id,
            status="executed_governed",
            action=tool.action,
            capability="create_directory",
            workspace=str(workspace),
            target_path=str(target),
            metadata={"created": not existed, "path": str(target)},
            warnings=list(decision["warnings"]),
            violations=list(decision["violations"]),
            trace=[*decision["trace"], {"stage": "filesystem_create_directory", "decision": "executed"}],
            side_effects=True,
            safe_to_execute=True,
            canonical_policy_decision=decision.get("canonical_policy"),
        )

    def _execute_shell(
        self,
        request: ToolExecutionRequest,
        tool: ToolDefinition,
        decision: dict[str, Any],
        *,
        execution_id: str,
        timeout: int,
    ) -> ToolExecutionResult:
        argv, parse_error = self._command_argv(request.input)
        if parse_error:
            decision["violations"].append(parse_error)
            return self._result_from_decision(request, decision, execution_id=execution_id)
        executable_error = self._executable_error(argv)
        if executable_error:
            decision["violations"].append(executable_error)
            return self._result_from_decision(request, decision, execution_id=execution_id)
        workspace = str(request.input.get("workspace") or "")
        classification = decision.get("shell_classification")
        shell_metadata = self._shell_metadata(classification)
        started = time.perf_counter()
        try:
            completed = self.runner(
                argv,
                cwd=workspace,
                timeout=timeout,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolExecutionResult(
                execution_id=execution_id,
                tool_id=request.tool_id,
                status="timeout",
                action=tool.action,
                capability=tool.capability,
                workspace=workspace,
                content=self._limit_text((exc.stdout or "") + (exc.stderr or "")),
                metadata={**shell_metadata, "timeout_seconds": timeout, "timeout": True, "duration_ms": int((time.perf_counter() - started) * 1000)},
                warnings=list(decision["warnings"]),
                violations=["tool_execution_timeout"],
                trace=[*decision["trace"], {"stage": "shell_command_finished", "decision": "timeout"}],
                side_effects=tool.side_effect,
                safe_to_execute=False,
            canonical_policy_decision=decision.get("canonical_policy"),
            )
        except Exception as exc:
            result = ToolExecutionResult(
                execution_id=execution_id,
                tool_id=request.tool_id,
                status="degraded",
                action=tool.action,
                capability=tool.capability,
                workspace=workspace,
                content=None,
                metadata={**shell_metadata, "error": exc.__class__.__name__, "duration_ms": int((time.perf_counter() - started) * 1000)},
                warnings=[*decision["warnings"], str(exc)],
                violations=["tool_execution_failed"],
                trace=[*decision["trace"], {"stage": "shell_adapter", "decision": "failed"}],
                side_effects=tool.side_effect,
                safe_to_execute=False,
            canonical_policy_decision=decision.get("canonical_policy"),
            )
            return result
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        status = "executed_governed" if completed.returncode == 0 else "degraded"
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolExecutionResult(
            execution_id=execution_id,
            tool_id=request.tool_id,
            status=status,
            action=tool.action,
            capability=tool.capability,
            workspace=workspace,
            content=self._limit_text(stdout if stdout else stderr),
            content_truncated=len(stdout if stdout else stderr) > self._max_output_chars(),
            metadata={
                **shell_metadata,
                "exit_code": completed.returncode,
                "stderr_preview": self._limit_text(stderr, max_chars=1000),
                "argv_length": len(argv),
                "duration_ms": duration_ms,
            },
            warnings=list(decision["warnings"]),
            violations=[] if completed.returncode == 0 else ["tool_exit_code_nonzero"],
            trace=[
                *decision["trace"],
                {"stage": "shell_command_started", "decision": "started", **shell_metadata},
                {"stage": "shell_command_finished", "decision": status, "exit_code": completed.returncode, "duration_ms": duration_ms},
            ],
            side_effects=tool.side_effect,
            safe_to_execute=completed.returncode == 0,
            canonical_policy_decision=decision.get("canonical_policy"),
        )

    @staticmethod
    def _shell_metadata(classification: Any) -> dict[str, Any]:
        if classification is None:
            return {}
        return {
            "command_id": getattr(classification, "command_id", None),
            "normalized_command": getattr(classification, "normalized_command", None),
            "shell_category": getattr(classification, "category", None),
            "shell_policy_decision": getattr(classification, "policy_decision", None),
            "risk_score": getattr(classification, "risk_score", None),
            "expected_side_effects": getattr(classification, "expected_side_effects", []),
        }

    def _post_validate_git_clone(
        self,
        request: ToolExecutionRequest,
        decision: dict[str, Any],
        result: ToolExecutionResult,
    ) -> ToolExecutionResult:
        workspace = str(request.input.get("workspace") or "")
        observed_remote = self._run_git_read(workspace, ["git", "remote", "get-url", "origin"])
        observed_branch = self._run_git_read(workspace, ["git", "branch", "--show-current"])
        remote_locator = str(observed_remote.stdout or "").strip()
        branch = str(observed_branch.stdout or "").strip()
        classification = decision.get("shell_classification")
        git_classification = getattr(classification, "git_classification", None)
        task_run = decision.get("task_run")
        post_scope = None
        if git_classification is not None:
            post_scope = self._git_scope_decision(
                task_run=task_run,
                request=request,
                git_classification=git_classification,
                git_observation={"remote_locator": remote_locator},
            )
        expected_branch = str(decision.get("git_branch") or "")
        metadata = dict(result.metadata)
        metadata.update({
            "observed_remote": remote_locator,
            "observed_branch": branch,
            "validated_branch": expected_branch,
        })
        if (
            observed_remote.returncode != 0
            or observed_branch.returncode != 0
            or not remote_locator
            or post_scope is None
            or post_scope.status != "allowed"
            or (expected_branch and branch != expected_branch)
        ):
            return result.model_copy(update={
                "status": "degraded",
                "safe_to_execute": False,
                "metadata": metadata,
                "violations": [*result.violations, "git_clone_post_validation_failed"],
            })
        return result.model_copy(update={"metadata": metadata})

    def _post_validate_git_push(
        self,
        request: ToolExecutionRequest,
        decision: dict[str, Any],
        result: ToolExecutionResult,
    ) -> ToolExecutionResult:
        workspace = str(request.input.get("workspace") or "")
        branch = str(decision.get("git_branch") or "")
        remote_name = "origin"
        classification = decision.get("shell_classification")
        git_classification = getattr(classification, "git_classification", None)
        if git_classification is not None and git_classification.remote_name:
            remote_name = str(git_classification.remote_name)
        local = self._run_git_read(workspace, ["git", "rev-parse", "HEAD"])
        remote = self._run_git_read(workspace, ["git", "ls-remote", remote_name, branch])
        local_head = str(local.stdout or "").strip()
        remote_line = str(remote.stdout or "").strip().splitlines()
        remote_head = remote_line[0].split()[0] if remote_line and remote_line[0].split() else ""
        metadata = dict(result.metadata)
        metadata.update({"local_head": local_head, "remote_head": remote_head, "validated_branch": branch})
        if local.returncode != 0 or remote.returncode != 0 or not local_head or not remote_head or local_head != remote_head:
            return result.model_copy(update={
                "status": "degraded",
                "safe_to_execute": False,
                "metadata": metadata,
                "violations": [*result.violations, "git_push_remote_head_mismatch"],
            })
        return result.model_copy(update={"metadata": metadata})

    def _execute_web(
        self,
        request: ToolExecutionRequest,
        tool: ToolDefinition,
        decision: dict[str, Any],
        *,
        execution_id: str,
        timeout: int,
    ) -> ToolExecutionResult:
        url = str(request.input.get("url") or "")
        method = str(request.input.get("method") or "GET").upper()
        network_error = self._network_error(url, method)
        if network_error:
            decision["violations"].append(network_error)
            return self._result_from_decision(request, decision, execution_id=execution_id)
        try:
            response = self.opener(Request(url, method=method), timeout=timeout)
            with response:
                body = response.read(self._max_output_chars() + 1)
                text = body.decode("utf-8", errors="replace")
                status_code = getattr(response, "status", None) or getattr(response, "code", None)
        except Exception as exc:
            return ToolExecutionResult(
                execution_id=execution_id,
                tool_id=request.tool_id,
                status="degraded",
                action=tool.action,
                capability=tool.capability,
                content=None,
                metadata={"url_host": urlparse(url).hostname, "method": method, "error": exc.__class__.__name__},
                warnings=[*decision["warnings"], str(exc)],
                violations=["web_request_failed"],
                trace=[*decision["trace"], {"stage": "web_adapter", "decision": "failed"}],
                side_effects=tool.side_effect,
                safe_to_execute=False,
            canonical_policy_decision=decision.get("canonical_policy"),
            )
        return ToolExecutionResult(
            execution_id=execution_id,
            tool_id=request.tool_id,
            status="executed_governed",
            action=tool.action,
            capability=tool.capability,
            content=self._limit_text(text),
            content_truncated=len(text) > self._max_output_chars(),
            metadata={"url_host": urlparse(url).hostname, "method": method, "http_status": status_code},
            warnings=list(decision["warnings"]),
            trace=[*decision["trace"], {"stage": "web_adapter", "decision": "executed_governed", "http_status": status_code}],
            side_effects=tool.side_effect,
            safe_to_execute=True,
            canonical_policy_decision=decision.get("canonical_policy"),
        )

    def _command_argv(self, payload: dict[str, Any]) -> tuple[list[str], str | None]:
        raw_argv = payload.get("argv")
        if isinstance(raw_argv, list) and all(isinstance(item, str) and item for item in raw_argv):
            return [str(item) for item in raw_argv], None
        command = str(payload.get("command") or "").strip()
        if not command:
            return [], "command_or_argv_required"
        denied = [str(item) for item in (self.policy.get("shell", {}) or {}).get("denied_tokens", []) or []]
        lowered = command.lower()
        for token in denied:
            if token.lower() in lowered:
                return [], "shell_metacharacter_denied"
        try:
            argv = shlex.split(command, posix=False)
        except ValueError:
            return [], "command_parse_failed"
        argv = [self._strip_wrapping_quotes(str(part)) for part in argv]
        return argv, None if argv else "command_or_argv_required"

    @staticmethod
    def _strip_wrapping_quotes(value: str) -> str:
        text = str(value)
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            return text[1:-1]
        return text

    def _executable_error(self, argv: list[str]) -> str | None:
        shell_policy = self.policy.get("shell", {}) if isinstance(self.policy, dict) else {}
        allowed = {str(item).lower() for item in shell_policy.get("allowed_executables", []) or []}
        denied = {str(item).lower() for item in shell_policy.get("denied_executables", []) or []}
        executable = Path(argv[0].strip('"')).name.lower() if argv else ""
        if executable in denied:
            return "executable_denied"
        if allowed and executable not in allowed:
            return "executable_not_allowlisted"
        return None

    def _network_error(self, url: str, method: str) -> str | None:
        network = self.policy.get("network", {}) if isinstance(self.policy, dict) else {}
        parsed = urlparse(url)
        if method not in set(network.get("allowed_methods", []) or []):
            return "network_method_not_allowed"
        if parsed.scheme.lower() in {str(item).lower() for item in network.get("denied_schemes", []) or []}:
            return "network_scheme_denied"
        if parsed.scheme.lower() not in {"http", "https"}:
            return "network_scheme_not_allowed"
        host = (parsed.hostname or "").lower()
        if not host:
            return "network_host_required"
        if host in {str(item).lower() for item in network.get("denied_hosts", []) or []}:
            return "network_host_denied"
        if host in {"localhost", "127.0.0.1", "::1"} and not bool(network.get("allow_localhost", False)):
            return "network_localhost_denied"
        return None

    def _workspace_error(
        self,
        workspace: str,
        *,
        local_resources: list,
        mission_bound: bool,
    ):
        if not workspace:
            return "workspace_required", None
        decision = self.workspace_roles.resolve_with_resources(
            workspace,
            local_resources=local_resources,
            required=True,
        )
        if mission_bound and decision.reason == "workspace_not_registered":
            return "workspace_not_declared_by_mission", decision
        if decision.status != "allowed" or decision.contract is None:
            return decision.reason, decision
        return None, decision

    def _timeout_seconds(self, request: ToolExecutionRequest) -> int:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        requested = int(request.input.get("timeout_seconds") or config.get("default_timeout_seconds", 30) or 30)
        maximum = int(config.get("max_timeout_seconds", 120) or 120)
        return max(1, min(requested, maximum))

    def _max_output_chars(self) -> int:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        return int(config.get("max_output_chars", 12000) or 12000)

    def _limit_text(self, value: str, *, max_chars: int | None = None) -> str:
        limit = max_chars or self._max_output_chars()
        if len(value) <= limit:
            return value
        return value[:limit] + f"\n...[truncated {len(value) - limit} chars]"

    def _result_from_decision(
        self,
        request: ToolExecutionRequest,
        decision: dict[str, Any],
        *,
        execution_id: str | None = None,
    ) -> ToolExecutionResult:
        tool = decision.get("tool")
        status = "invalid" if "unknown_tool" in decision.get("violations", []) else "blocked"
        return ToolExecutionResult(
            execution_id=execution_id or f"exec_{uuid4().hex}",
            tool_id=request.tool_id,
            status=status,
            action=tool.action if isinstance(tool, ToolDefinition) else None,
            capability=tool.capability if isinstance(tool, ToolDefinition) else None,
            workspace=str(request.input.get("workspace") or "") or None,
            target_path=str(request.input.get("path") or "") or None,
            warnings=list(decision.get("warnings", [])),
            violations=list(decision.get("violations", [])),
            trace=list(decision.get("trace", [])),
            side_effects=bool(tool.side_effect) if isinstance(tool, ToolDefinition) else False,
            safe_to_execute=False,
            canonical_policy_decision=decision.get("canonical_policy"),
        )

    def _policy_snapshot(self, request: ToolExecutionRequest, tool: ToolDefinition, decision: dict[str, Any]) -> ApprovalPolicySnapshot:
        fingerprint = self._request_fingerprint(request)
        trace_hash = hashlib.sha256(json.dumps(decision.get("trace", []), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return ApprovalPolicySnapshot(
            policy_status="approval_required",
            allowed_actions=[tool.action],
            denied_actions=list((self.policy.get("governed_tool_execution", {}) or {}).get("denied_actions", []) or []),
            approval_required_for=[tool.action],
            granted_capabilities=[tool.capability],
            denied_capabilities=list((self.policy.get("governed_tool_execution", {}) or {}).get("denied_capabilities", []) or []),
            workspace_status="governed_allowlisted",
            risk_level=tool.risk_level,
            trace_hash=trace_hash,
            config_versions={
                "governed_tool_execution_policy": int(self.policy.get("schema_version", 1) or 1),
                "tool_id": tool.tool_id,
                "tool_action": tool.action,
                "tool_execution_request_hash": fingerprint,
            },
        )

    def _request_fingerprint(self, request: ToolExecutionRequest) -> str:
        payload = {
            "tool_id": request.tool_id,
            "input": request.input,
            "mode": "governed",
            "task_run_id": request.task_run_id,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def status(self) -> dict[str, object]:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        return {
            "status": "ok" if config.get("enabled", False) else "disabled",
            "service": "governed_tool_execution",
            "mode": config.get("mode", "unknown"),
            "approval_required": bool(config.get("require_approval", True)),
            "audit_required": bool(config.get("require_audit", True)),
            "allowed_actions": list(config.get("allowed_actions", []) or []),
            "denied_actions": list(config.get("denied_actions", []) or []),
            "shell_free": True,
            "uses_shell_true": False,
            "timeout_seconds": {
                "default": config.get("default_timeout_seconds"),
                "max": config.get("max_timeout_seconds"),
            },
        }
