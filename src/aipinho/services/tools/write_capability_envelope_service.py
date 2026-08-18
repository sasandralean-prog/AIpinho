from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.tools.write_capability_envelope import WriteCapabilityEnvelope, WriteCapabilityEnvelopeDecision
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.services.session.session_store import utc_now
from aipinho.utils.safe_paths import resolve_within_root


class WriteCapabilityEnvelopeService:
    PREVIEW_REQUIRED = {"create_file", "modify_file", "delete_file", "create_directory", "move_file", "apply_patch", "run_shell_write"}
    APPROVAL_STRONG_REQUIRED = {"delete_file", "move_file", "run_shell_write"}
    CAPABILITY_BY_OPERATION = {
        "create_file": "write_workspace",
        "modify_file": "write_workspace",
        "delete_file": "write_workspace",
        "create_directory": "write_workspace",
        "move_file": "write_workspace",
        "apply_patch": "patch_apply",
        "run_shell_write": "shell",
        "run_shell_test": "shell",
        "run_shell_build": "shell",
        "run_shell_readonly": "shell",
    }

    def __init__(self, workspace_roles: WorkspaceRoleContractService | None = None) -> None:
        self.workspace_roles = workspace_roles or WorkspaceRoleContractService().load()

    def create(self, *, workspace_path: str, operation_type: str, target_path: str | None = None, task_id: str | None = None, session_id: str | None = None, preview_id: str | None = None, approval_id: str | None = None, policy_decision_id: str | None = None, actor: str = "system", expected_side_effects: list[str] | None = None, risk_score: str = "medium") -> WriteCapabilityEnvelopeDecision:
        workspace = self.workspace_roles.resolve(workspace_path)
        blocking: list[str] = []
        warnings: list[str] = []
        trace: list[dict[str, object]] = list(workspace.trace)
        if workspace.status != "allowed" or workspace.contract is None:
            blocking.append(workspace.reason)
        contract = workspace.contract
        workspace_id = contract.workspace_id if contract is not None else "unknown"
        workspace_role = contract.role if contract is not None else "forbidden"
        safe_operation_type = operation_type if operation_type in self.CAPABILITY_BY_OPERATION else "run_shell_readonly"
        capability = self.CAPABILITY_BY_OPERATION.get(operation_type, "unknown")
        if capability == "unknown":
            blocking.append("unknown_write_operation")
        if contract is not None:
            allowed, reason = self.workspace_roles.operation_allowed(contract, operation_type)
            trace.append({"stage": "write_capability_envelope", "decision": "allowed" if allowed else "denied", "reason": reason, "data": {"operation_type": operation_type, "workspace_id": contract.workspace_id}})
            if not allowed:
                blocking.append(reason)
            if target_path:
                path_reason = self._target_path_reason(target_path, contract.root_path)
                if path_reason:
                    blocking.append(path_reason)
        if operation_type in self.PREVIEW_REQUIRED and not preview_id:
            blocking.append("preview_required_for_side_effect")
        if contract is not None and contract.approval_required and operation_type in self.PREVIEW_REQUIRED and not approval_id:
            blocking.append("approval_required_for_side_effect")
        if operation_type in self.APPROVAL_STRONG_REQUIRED and not approval_id:
            blocking.append("strong_approval_required_for_operation")
        status = "blocked" if blocking else ("approval_required" if not approval_id and operation_type in self.PREVIEW_REQUIRED else "valid")
        envelope = WriteCapabilityEnvelope(
            task_id=task_id,
            session_id=session_id,
            workspace_id=workspace_id,
            workspace_role=workspace_role,
            target_path=target_path,
            operation_type=safe_operation_type,  # type: ignore[arg-type]
            capability_required=capability,
            policy_decision_id=policy_decision_id,
            approval_id=approval_id,
            preview_id=preview_id,
            expected_side_effects=expected_side_effects or self._default_side_effects(operation_type, target_path),
            risk_score=risk_score,
            actor=actor,
            created_at=utc_now(),
            status=status,  # type: ignore[arg-type]
            blocking_reasons=list(dict.fromkeys(blocking)),
            warnings=warnings,
            trace=trace,
        )
        return WriteCapabilityEnvelopeDecision(allowed=not blocking, envelope=envelope, reason="write_envelope_valid" if not blocking else "write_envelope_blocked")

    def _target_path_reason(self, target_path: str, workspace_root: str) -> str | None:
        try:
            resolved = resolve_within_root(Path(target_path), Path(workspace_root))
        except Exception:
            return "target_path_outside_workspace"
        if resolved.is_symlink():
            return "target_path_symlink_blocked_until_policy_exists"
        return None

    def _default_side_effects(self, operation_type: str, target_path: str | None) -> list[str]:
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
        }
