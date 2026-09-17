from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.config_governance.workspace_permission import WorkspacePermissionDecision
from aipinho.schemas.governance.lifecycle import (
    CanonicalOperationContract,
    CanonicalPermission,
    CanonicalPolicyFacet,
)
from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.tools.write_capability_envelope import (
    WriteCapabilityEnvelope,
    WriteCapabilityEnvelopeDecision,
)
from aipinho.services.config_governance.workspace_permission_matrix_service import (
    WorkspacePermissionMatrixService,
)
from aipinho.services.governance.policy.effective_policy_decision_service import (
    EffectivePolicyDecisionService,
)
from aipinho.services.policy_kernel.workspace_role_contract_service import (
    WorkspaceRoleContractService,
)
from aipinho.services.session.session_store import utc_now
from aipinho.utils.safe_paths import resolve_within_root


class WriteCapabilityEnvelopeService:
    PREVIEW_REQUIRED = {
        "create_file",
        "modify_file",
        "delete_file",
        "create_directory",
        "move_file",
        "apply_patch",
        "run_shell_write",
    }
    APPROVAL_STRONG_REQUIRED = {
        "delete_file",
        "move_file",
        "run_shell_write",
    }
    CAPABILITY_BY_OPERATION = {
        "create_file": "create_file",
        "modify_file": "modify_file",
        "delete_file": "delete_file",
        "create_directory": "create_directory",
        "move_file": "move_file",
        "apply_patch": "apply_patch",
        "run_shell_write": "script_execution",
        "run_shell_test": "shell_test",
        "run_shell_build": "shell_build",
        "run_shell_readonly": "shell_readonly",
    }

    def __init__(
        self,
        workspace_roles: WorkspaceRoleContractService | None = None,
        permission_matrix: WorkspacePermissionMatrixService | None = None,
        effective_policy: EffectivePolicyDecisionService | None = None,
    ) -> None:
        self.workspace_roles = workspace_roles or WorkspaceRoleContractService().load()
        self.permission_matrix = permission_matrix or WorkspacePermissionMatrixService().load()
        self.effective_policy = effective_policy or EffectivePolicyDecisionService()

    def create(
        self,
        *,
        workspace_path: str,
        operation_type: str,
        target_path: str | None = None,
        task_id: str | None = None,
        session_id: str | None = None,
        preview_id: str | None = None,
        approval_id: str | None = None,
        policy_decision_id: str | None = None,
        actor: str = "system",
        expected_side_effects: list[str] | None = None,
        risk_score: str = "medium",
        local_resources: list[MissionResourceScope] | None = None,
        human_authority_effective: bool | None = None,
    ) -> WriteCapabilityEnvelopeDecision:
        resources = list(local_resources or [])
        workspace = self.workspace_roles.resolve_with_resources(
            workspace_path,
            local_resources=resources,
        )
        facets: list[CanonicalPolicyFacet] = []
        warnings: list[str] = []
        trace: list[dict[str, object]] = list(workspace.trace)
        capability = self.CAPABILITY_BY_OPERATION.get(operation_type)
        resource_id = workspace.contract.workspace_id if workspace.contract is not None else None
        facets.append(
            CanonicalPolicyFacet(
                facet="capability_demand",
                permission=CanonicalPermission.ALLOWED,
                source="write_capability_envelope",
                reason_code="capability_requested",
                capability=capability or "unknown",
                resource_id=resource_id,
                details={"operation_type": operation_type},
            )
        )
        if capability is None:
            facets.append(
                CanonicalPolicyFacet(
                    facet="global_policy",
                    permission=CanonicalPermission.DENIED,
                    source="write_capability_envelope",
                    reason_code="unknown_write_operation",
                    capability="unknown",
                    resource_id=resource_id,
                )
            )

        contract = workspace.contract
        if workspace.status != "allowed" or contract is None:
            facets.append(
                CanonicalPolicyFacet(
                    facet="workspace_resolution",
                    permission=CanonicalPermission.DENIED,
                    source="workspace_role_contract",
                    reason_code=workspace.reason,
                    capability=capability,
                    resource_id=resource_id,
                    trace=list(workspace.trace),
                )
            )
        else:
            allowed, role_reason = self.workspace_roles.operation_allowed(contract, operation_type)
            facets.append(
                CanonicalPolicyFacet(
                    facet="workspace_role",
                    permission=CanonicalPermission.ALLOWED if allowed else CanonicalPermission.DENIED,
                    source="workspace_role_contract",
                    reason_code=role_reason,
                    capability=capability,
                    resource_id=resource_id,
                )
            )
            if target_path:
                path_reason = self._target_path_reason(target_path, contract.root_path)
                facets.append(
                    CanonicalPolicyFacet(
                        facet="target_path",
                        permission=(
                            CanonicalPermission.DENIED
                            if path_reason
                            else CanonicalPermission.ALLOWED
                        ),
                        source="write_capability_envelope",
                        reason_code=path_reason or "target_path_within_workspace",
                        capability=capability,
                        resource_id=resource_id,
                    )
                )

        resource_decision: WorkspacePermissionDecision | None = None
        if resources and capability is not None:
            resource_decision = self.permission_matrix.decide_with_resources(
                path=target_path or workspace_path,
                permission=capability,
                local_resources=resources,
            )
            resource_permission = (
                CanonicalPermission.DENIED
                if resource_decision.status == "denied"
                else CanonicalPermission.ASK
                if resource_decision.status == "approval_required"
                else CanonicalPermission.ALLOWED
            )
            facets.append(
                CanonicalPolicyFacet(
                    facet="resource_permission",
                    permission=resource_permission,
                    source="workspace_permission_matrix",
                    reason_code=resource_decision.reason_code,
                    capability=capability,
                    resource_id=resource_decision.workspace_id,
                    requires_human_authority=(
                        resource_decision.status == "approval_required"
                    ),
                    trace=list(resource_decision.trace),
                )
            )
            resource_id = resource_decision.workspace_id or resource_id

        if operation_type in self.PREVIEW_REQUIRED:
            facets.append(
                CanonicalPolicyFacet(
                    facet="preview_evidence",
                    permission=(
                        CanonicalPermission.ALLOWED
                        if preview_id
                        else CanonicalPermission.DENIED
                    ),
                    source="write_capability_envelope",
                    reason_code=(
                        "preview_bound"
                        if preview_id
                        else "preview_required_for_side_effect"
                    ),
                    capability=capability,
                    resource_id=resource_id,
                )
            )

        resource_requires_human = (
            resource_decision is not None
            and resource_decision.status == "approval_required"
        )
        role_requires_human = bool(
            contract is not None
            and contract.approval_required
            and operation_type in self.PREVIEW_REQUIRED
        )
        strong_requires_human = operation_type in self.APPROVAL_STRONG_REQUIRED
        requires_human = (
            resource_requires_human
            or role_requires_human
            or strong_requires_human
        )
        if requires_human:
            facets.append(
                CanonicalPolicyFacet(
                    facet="human_authority_requirement",
                    permission=CanonicalPermission.ASK,
                    source="write_capability_envelope",
                    reason_code="approval_required_for_side_effect",
                    capability=capability,
                    resource_id=resource_id,
                    requires_human_authority=True,
                )
            )
            if human_authority_effective or approval_id:
                facets.append(
                    CanonicalPolicyFacet(
                        facet="human_authority",
                        permission=CanonicalPermission.ALLOWED,
                        source=(
                            "mission_authority_grant"
                            if human_authority_effective
                            else "approval_binding"
                        ),
                        reason_code=(
                            "grant_effective"
                            if human_authority_effective
                            else "approval_binding_present"
                        ),
                        capability=capability,
                        resource_id=resource_id,
                    )
                )

        operation_contract = CanonicalOperationContract(
            session_id=session_id,
            source_channel=actor,
            intent_type="governed_write",
            operation_type=operation_type,
            contract_type="write_capability_envelope",
            runtime_profile="governed_write",
            requires_task=bool(task_id),
            workspace_mutation=operation_type != "run_shell_readonly",
            requested_actions=[operation_type],
            target_paths=[target_path] if target_path else [],
            workspace_path=workspace_path,
            risk_level=risk_score,
        )
        canonical = self.effective_policy.resolve_facets(
            operation_contract,
            facets=facets,
            capability=capability or "unknown",
            resource_id=resource_id,
        )

        blocking = [
            str(item.reason_code)
            for item in facets
            if item.permission == CanonicalPermission.DENIED
        ]
        if canonical.permission == CanonicalPermission.ASK:
            blocking.append("approval_required_for_side_effect")
        blocking = list(dict.fromkeys(item for item in blocking if item))

        status = (
            "valid"
            if canonical.permission == CanonicalPermission.ALLOWED
            else "approval_required"
            if canonical.permission == CanonicalPermission.ASK
            else "blocked"
        )
        safe_operation_type = (
            operation_type
            if operation_type in self.CAPABILITY_BY_OPERATION
            else "run_shell_readonly"
        )
        envelope = WriteCapabilityEnvelope(
            task_id=task_id,
            session_id=session_id,
            workspace_id=resource_id or "unknown",
            workspace_role=(contract.role if contract is not None else "forbidden"),
            target_path=target_path,
            operation_type=safe_operation_type,  # type: ignore[arg-type]
            capability_required=capability or "unknown",
            policy_decision_id=policy_decision_id,
            approval_id=approval_id,
            preview_id=preview_id,
            expected_side_effects=(
                expected_side_effects
                or self._default_side_effects(operation_type, target_path)
            ),
            risk_score=risk_score,
            actor=actor,
            created_at=utc_now(),
            status=status,  # type: ignore[arg-type]
            blocking_reasons=blocking,
            warnings=warnings,
            trace=[
                *trace,
                *canonical.trace,
            ],
        )
        return WriteCapabilityEnvelopeDecision(
            allowed=canonical.permission == CanonicalPermission.ALLOWED,
            envelope=envelope,
            reason=(
                "write_envelope_valid"
                if canonical.permission == CanonicalPermission.ALLOWED
                else "write_envelope_approval_required"
                if canonical.permission == CanonicalPermission.ASK
                else "write_envelope_blocked"
            ),
            canonical_policy_decision=canonical,
        )

    def _target_path_reason(self, target_path: str, workspace_root: str) -> str | None:
        try:
            resolved = resolve_within_root(Path(target_path), Path(workspace_root))
        except Exception:
            return "target_path_outside_workspace"
        if resolved.is_symlink():
            return "target_path_symlink_blocked_until_policy_exists"
        return None

    def _default_side_effects(
        self,
        operation_type: str,
        target_path: str | None,
    ) -> list[str]:
        if operation_type == "run_shell_readonly":
            return []
        if operation_type.startswith("run_shell"):
            return [operation_type]
        if target_path:
            return [f"{operation_type}:{target_path}"]
        return [operation_type]

    def status(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "write_capability_envelope",
            "preview_required_for": sorted(self.PREVIEW_REQUIRED),
            "strong_approval_required_for": sorted(self.APPROVAL_STRONG_REQUIRED),
            "decision_authority": "effective_policy_decision",
        }
