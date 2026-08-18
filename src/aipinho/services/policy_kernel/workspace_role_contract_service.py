from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.policy.workspace_role_contract import WorkspaceRoleContract, WorkspaceRoleDecision
from aipinho.utils.yaml_loader import load_yaml_file


class WorkspaceRoleContractService:
    READ_ONLY_OPERATIONS = {"read_workspace", "inspect_files", "analyze", "list_files", "search_files"}
    ROLE_RESTRICTIVENESS = {
        "forbidden": 5,
        "protected": 4,
        "source_readonly": 3,
        "external_inbox": 3,
        "target_mutable": 2,
        "artifact_output": 2,
        "temp_staging": 2,
        "system_mutable": 1,
    }

    SAFE_DEFAULTS: dict[str, dict[str, object]] = {
        "source_readonly": {
            "read_allowed": True,
            "write_allowed": False,
            "shell_allowed": False,
            "patch_allowed": False,
            "approval_required": False,
            "allowed_operations": ["read_workspace", "inspect_files", "analyze", "run_shell_readonly"],
            "forbidden_operations": ["create_file", "modify_file", "delete_file", "move_file", "apply_patch", "run_shell_write"],
            "max_risk_without_approval": "low",
        },
        "target_mutable": {
            "read_allowed": True,
            "write_allowed": True,
            "shell_allowed": True,
            "patch_allowed": True,
            "approval_required": True,
            "allowed_operations": ["read_workspace", "create_file", "modify_file", "apply_patch", "run_shell_readonly", "run_shell_test", "run_shell_build"],
            "forbidden_operations": ["delete_file", "move_file", "git_write_shell", "destructive_shell"],
            "max_risk_without_approval": "low",
        },
        "external_inbox": {
            "read_allowed": True,
            "write_allowed": False,
            "shell_allowed": False,
            "patch_allowed": False,
            "approval_required": False,
            "allowed_operations": ["read_workspace", "inspect_files", "analyze", "copy_from"],
            "forbidden_operations": ["create_file", "modify_file", "delete_file", "move_file", "apply_patch", "run_shell_write"],
            "max_risk_without_approval": "low",
        },
        "artifact_output": {
            "read_allowed": True,
            "write_allowed": False,
            "shell_allowed": False,
            "patch_allowed": False,
            "approval_required": True,
            "allowed_operations": ["read_workspace", "artifact_create"],
            "forbidden_operations": ["delete_file", "move_file", "apply_patch", "run_shell_write", "destructive_shell"],
            "max_risk_without_approval": "low",
        },
        "temp_staging": {
            "read_allowed": True,
            "write_allowed": False,
            "shell_allowed": False,
            "patch_allowed": False,
            "approval_required": True,
            "allowed_operations": ["read_workspace", "inspect_files", "analyze"],
            "forbidden_operations": ["delete_file", "move_file", "git_write_shell", "destructive_shell"],
            "max_risk_without_approval": "low",
        },
        "system_mutable": {
            "read_allowed": True,
            "write_allowed": True,
            "shell_allowed": True,
            "patch_allowed": True,
            "approval_required": True,
            "allowed_operations": ["read_workspace", "create_file", "modify_file", "apply_patch", "run_shell_readonly", "run_shell_test", "run_shell_build", "process_control_shell"],
            "forbidden_operations": ["delete_file", "move_file", "git_write_shell", "destructive_shell"],
            "max_risk_without_approval": "low",
        },
        "protected": {
            "read_allowed": True,
            "write_allowed": False,
            "shell_allowed": False,
            "patch_allowed": False,
            "approval_required": True,
            "allowed_operations": ["read_workspace", "run_shell_readonly"],
            "forbidden_operations": ["create_file", "modify_file", "delete_file", "move_file", "apply_patch", "run_shell_write", "destructive_shell"],
            "max_risk_without_approval": "none",
        },
        "forbidden": {
            "read_allowed": False,
            "write_allowed": False,
            "shell_allowed": False,
            "patch_allowed": False,
            "approval_required": True,
            "allowed_operations": [],
            "forbidden_operations": ["read_workspace", "create_file", "modify_file", "delete_file", "move_file", "apply_patch", "run_shell_write", "destructive_shell"],
            "max_risk_without_approval": "none",
        },
    }

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "workspaces" / "workspace_registry.yaml"
        self._config: dict[str, Any] | None = None

    def load(self) -> "WorkspaceRoleContractService":
        if self.config_path.exists() and self.config_path.stat().st_size > 0:
            self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        else:
            self._config = {"schema_version": 1, "workspaces": []}
        return self

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config or {"schema_version": 1, "workspaces": []}

    def resolve(self, path: str | None, *, required: bool = True) -> WorkspaceRoleDecision:
        if not path:
            return WorkspaceRoleDecision(
                status="needs_clarification" if required else "allowed",
                reason="workspace_missing" if required else "workspace_not_required",
                trace=[self._trace("workspace_role_contract", "needs_clarification" if required else "allowed", "workspace_missing" if required else "workspace_not_required")],
            )
        normalized_path = self._normalize(path)
        matches: list[tuple[int, int, dict[str, Any], str]] = []
        for entry in self.config.get("workspaces", []) or []:
            if not isinstance(entry, dict):
                continue
            root = str(entry.get("root_path") or "")
            if root and self._is_under(normalized_path, root):
                role = str(entry.get("role") or "forbidden")
                matches.append(
                    (
                        len(self._normalize(root)),
                        self.ROLE_RESTRICTIVENESS.get(role, self.ROLE_RESTRICTIVENESS["forbidden"]),
                        entry,
                        root,
                    )
                )
        if not matches:
            contract = self._contract_from_entry(
                {
                    "workspace_id": "unregistered_workspace",
                    "root_path": path,
                    "role": "forbidden",
                    "human_label": "Unregistered workspace",
                    "reason": "Workspace is not registered for governed operations.",
                },
                matched_root=None,
                path_within_workspace=False,
            )
            return WorkspaceRoleDecision(
                status="denied",
                contract=contract,
                reason="workspace_not_registered",
                trace=[self._trace("workspace_role_contract", "denied", "workspace_not_registered", {"path": path})],
            )
        _length, _restrictiveness, entry, matched_root = sorted(
            matches,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )[0]
        contract = self._contract_from_entry(entry, matched_root=matched_root, path_within_workspace=True)
        status = "denied" if contract.role in {"forbidden"} else "allowed"
        candidates = [
            {
                "workspace_id": str(candidate.get("workspace_id") or ""),
                "root_path": candidate_root,
                "role": str(candidate.get("role") or "forbidden"),
                "root_length": root_length,
                "restrictiveness": restrictiveness,
            }
            for root_length, restrictiveness, candidate, candidate_root in sorted(
                matches,
                key=lambda item: (item[0], item[1]),
                reverse=True,
            )
        ]
        return WorkspaceRoleDecision(
            status=status,
            contract=contract,
            reason=contract.reason or f"workspace_role_{contract.role}",
            trace=[
                self._trace(
                    "workspace_role_contract",
                    status,
                    contract.reason or contract.role,
                    {
                        "workspace_id": contract.workspace_id,
                        "role": contract.role,
                        "selection_rule": "longest_path_then_deny_override",
                        "candidates": candidates,
                    },
                )
            ],
        )

    def operation_allowed(self, contract: WorkspaceRoleContract, operation_type: str) -> tuple[bool, str]:
        if operation_type in set(contract.forbidden_operations):
            return False, "operation_forbidden_by_workspace_role"
        if operation_type in self.READ_ONLY_OPERATIONS:
            if contract.read_allowed:
                return True, "workspace_role_allows_read_operation"
            return False, "workspace_role_denies_read"
        if contract.allowed_operations and operation_type not in set(contract.allowed_operations):
            return False, "operation_not_allowed_by_workspace_role"
        if operation_type in {"create_file", "modify_file", "delete_file", "move_file", "apply_patch", "run_shell_write"} and not contract.write_allowed:
            return False, "workspace_role_denies_write"
        if operation_type == "apply_patch" and not contract.patch_allowed:
            return False, "workspace_role_denies_patch"
        if operation_type == "run_shell_readonly" and not contract.read_allowed:
            return False, "workspace_role_denies_readonly_shell"
        if operation_type.startswith("run_shell") and operation_type != "run_shell_readonly" and not contract.shell_allowed:
            return False, "workspace_role_denies_shell"
        return True, "workspace_role_allows_operation"

    def _contract_from_entry(self, entry: dict[str, Any], *, matched_root: str | None, path_within_workspace: bool) -> WorkspaceRoleContract:
        role = str(entry.get("role") or "forbidden")
        defaults = dict(self.SAFE_DEFAULTS.get(role, self.SAFE_DEFAULTS["forbidden"]))
        payload = {
            **defaults,
            **entry,
            "workspace_id": str(entry.get("workspace_id") or self._workspace_id(entry.get("root_path"), role)),
            "root_path": str(entry.get("root_path") or ""),
            "role": role,
            "human_label": str(entry.get("human_label") or entry.get("label") or role),
            "reason": str(entry.get("reason") or f"workspace_role_{role}"),
            "evidence": [str(item) for item in entry.get("evidence", []) or []],
            "matched_root": matched_root,
            "path_within_workspace": path_within_workspace,
        }
        allowed_fields = set(WorkspaceRoleContract.model_fields.keys())
        return WorkspaceRoleContract(**{key: value for key, value in payload.items() if key in allowed_fields})

    def _workspace_id(self, root_path: object, role: str) -> str:
        leaf = Path(str(root_path or role)).name or role
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in leaf).strip("_")
        return safe or role

    def _normalize(self, value: str) -> str:
        return os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))

    def _is_under(self, normalized_path: str, root: str) -> bool:
        normalized_root = self._normalize(root)
        return normalized_path == normalized_root or normalized_path.startswith(normalized_root + os.sep)

    def _trace(self, stage: str, decision: str, reason: str, data: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "stage": stage,
            "decision": decision,
            "reason": reason,
            "source": str(self.config_path),
            "data": data or {},
        }

    def status(self) -> dict[str, object]:
        workspaces = [item for item in self.config.get("workspaces", []) or [] if isinstance(item, dict)]
        roles = sorted({str(item.get("role", "unknown")) for item in workspaces})
        return {"status": "ok", "service": "workspace_role_contract", "workspaces": len(workspaces), "roles": roles}
