from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from aipinho.core.paths import PATHS
from aipinho.schemas.config_governance.workspace_permission import (
    PermissionName,
    PermissionValue,
    WorkspaceEntry,
    WorkspacePermissionDecision,
    WorkspacePreviewRequest,
    WorkspaceRegistryRole,
)
from aipinho.utils.yaml_loader import load_yaml_file


ALL_PERMISSIONS: tuple[PermissionName, ...] = (
    "read_file",
    "list_files",
    "create_file",
    "modify_file",
    "apply_patch",
    "artifact_create",
    "copy_from",
    "copy_to",
    "move_from",
    "move_to",
    "delete_file",
    "shell_readonly",
    "shell_build",
    "shell_test",
    "script_execution",
    "network_download",
    "git_commit",
    "git_push",
)


def _all(value: PermissionValue) -> dict[PermissionName, PermissionValue]:
    return {permission: value for permission in ALL_PERMISSIONS}


ROLE_DEFAULTS: dict[WorkspaceRegistryRole, dict[PermissionName, PermissionValue]] = {
    "source_readonly": {
        **_all("denied"),
        "read_file": "allowed",
        "list_files": "allowed",
        "copy_from": "allowed",
        "artifact_create": "ask",
        "shell_readonly": "ask",
    },
    "target_mutable": {
        **_all("ask"),
        "read_file": "allowed",
        "list_files": "allowed",
        "copy_from": "allowed",
        "delete_file": "ask",
        "git_push": "denied",
    },
    "external_inbox": {
        **_all("denied"),
        "read_file": "allowed",
        "list_files": "allowed",
        "copy_from": "allowed",
        "artifact_create": "ask",
    },
    "artifact_output": {
        **_all("denied"),
        "read_file": "allowed",
        "list_files": "allowed",
        "create_file": "ask",
        "modify_file": "ask",
        "artifact_create": "ask",
        "copy_to": "ask",
    },
    "system_mutable": {
        **_all("ask"),
        "read_file": "allowed",
        "list_files": "allowed",
        "copy_from": "allowed",
        "git_push": "denied",
    },
    "protected": {
        **_all("denied"),
        "read_file": "ask",
        "list_files": "ask",
        "copy_from": "ask",
        "artifact_create": "ask",
        "shell_readonly": "ask",
    },
    "temp_staging": {
        **_all("ask"),
        "read_file": "allowed",
        "list_files": "allowed",
        "copy_from": "allowed",
        "git_push": "denied",
    },
    "forbidden": _all("denied"),
}

ACTION_PERMISSION_ALIASES: dict[str, PermissionName] = {
    "read_workspace": "read_file",
    "read_file": "read_file",
    "read_files": "read_file",
    "inspect_files": "read_file",
    "analyze": "read_file",
    "list_files": "list_files",
    "search_files": "list_files",
    "create_file": "create_file",
    "write_file": "create_file",
    "write_files": "modify_file",
    "modify_file": "modify_file",
    "modify_files": "modify_file",
    "apply_patch": "apply_patch",
    "patch_apply": "apply_patch",
    "artifact_create": "artifact_create",
    "artifact_generate": "artifact_create",
    "copy_from": "copy_from",
    "copy_to": "copy_to",
    "move_from": "move_from",
    "move_to": "move_to",
    "delete_file": "delete_file",
    "delete_files": "delete_file",
    "run_shell_readonly": "shell_readonly",
    "shell_readonly": "shell_readonly",
    "run_shell_build": "shell_build",
    "shell_build": "shell_build",
    "run_shell_test": "shell_test",
    "run_tests": "shell_test",
    "shell_test": "shell_test",
    "script_execution": "script_execution",
    "run_command": "script_execution",
    "shell": "script_execution",
    "network_download": "network_download",
    "web_request": "network_download",
    "git_commit": "git_commit",
    "git_push": "git_push",
}


class WorkspacePermissionMatrixService:
    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or PATHS.config_root / "workspaces" / "workspace_registry.yaml"
        self._config: dict[str, Any] | None = None

    def load(self) -> "WorkspacePermissionMatrixService":
        if self.registry_path.exists() and self.registry_path.stat().st_size > 0:
            self._config = load_yaml_file(self.registry_path, critical=True, root=self.registry_path.parent)
        else:
            self._config = self.empty_registry()
        return self

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config or self.empty_registry()

    def empty_registry(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "defaults": {
                "unregistered_role": "forbidden",
                "prefer_longest_root_match": True,
                "deny_overrides_allow": True,
            },
            "role_defaults": self.role_defaults_from_static(),
            "workspaces": [],
        }

    def role_defaults_from_static(self) -> dict[str, dict[str, str]]:
        return {role: dict(values) for role, values in ROLE_DEFAULTS.items()}

    def role_defaults(self) -> dict[str, dict[str, str]]:
        configured = self.config.get("role_defaults")
        if not isinstance(configured, dict):
            return self.role_defaults_from_static()
        merged: dict[str, dict[str, str]] = {}
        for role, defaults in ROLE_DEFAULTS.items():
            role_overrides = configured.get(role, {})
            merged[role] = {
                permission: str((role_overrides or {}).get(permission, value))
                for permission, value in defaults.items()
            }
        return merged

    def effective_policy(self) -> dict[str, Any]:
        registry = dict(self.config)
        registry["role_defaults"] = self.role_defaults()
        registry["permissions"] = list(ALL_PERMISSIONS)
        registry["decision_rule"] = "longest_path_then_deny_override"
        return registry

    def validate_registry(self, registry: dict[str, Any] | None = None) -> list[str]:
        payload = registry or self.config
        errors: list[str] = []
        seen: set[str] = set()
        for item in payload.get("workspaces", []) or []:
            if not isinstance(item, dict):
                errors.append("workspace_entry_must_be_mapping")
                continue
            workspace_id = str(item.get("workspace_id") or "").strip()
            if not workspace_id:
                errors.append("workspace_id_required")
            if workspace_id in seen:
                errors.append(f"workspace_id_duplicate:{workspace_id}")
            seen.add(workspace_id)
            root_path = str(item.get("root_path") or "").strip()
            if not root_path:
                errors.append(f"root_path_required:{workspace_id or '<missing>'}")
            else:
                path = Path(root_path).expanduser()
                if not path.is_absolute():
                    errors.append(f"root_path_must_be_absolute:{workspace_id or root_path}")
                if ".." in path.parts:
                    errors.append(f"path_traversal_not_allowed:{workspace_id or root_path}")
            role = str(item.get("role") or "")
            if role not in ROLE_DEFAULTS:
                errors.append(f"workspace_role_invalid:{workspace_id or role}")
            permissions = item.get("permissions", {}) or {}
            if not isinstance(permissions, dict):
                errors.append(f"permissions_must_be_mapping:{workspace_id or root_path}")
            else:
                for permission, value in permissions.items():
                    if permission not in ALL_PERMISSIONS:
                        errors.append(f"permission_unknown:{workspace_id}:{permission}")
                    if value not in {"allowed", "ask", "denied"}:
                        errors.append(f"permission_value_invalid:{workspace_id}:{permission}")
        return errors

    def preview_workspace(self, request: WorkspacePreviewRequest) -> dict[str, object]:
        entry = WorkspaceEntry(
            workspace_id=request.workspace_id or self.workspace_id_for_path(request.root_path),
            root_path=str(Path(request.root_path).expanduser().resolve(strict=False)),
            role=request.role,
            permissions=request.permissions,
            reason="workspace_preview",
        )
        registry = dict(self.config)
        workspaces = [item for item in registry.get("workspaces", []) or [] if isinstance(item, dict)]
        workspaces.append(entry.model_dump())
        registry["workspaces"] = workspaces
        errors = self.validate_registry(registry)
        decision = self.decide(path=entry.root_path, permission="read_file", registry=registry)
        return {"status": "ok" if not errors else "invalid", "entry": entry.model_dump(), "validation_errors": errors, "sample_decision": decision.model_dump()}

    def decide(
        self,
        *,
        path: str | None,
        permission: PermissionName | str,
        registry: dict[str, Any] | None = None,
    ) -> WorkspacePermissionDecision:
        permission_name = self.permission_for_action(permission)
        if not path:
            return self._decision("denied", "workspace_not_registered", permission_name, "denied", None, None, None, None)
        selected = self._select_workspace(path, registry=registry)
        if selected is None:
            return self._decision("denied", "workspace_not_registered", permission_name, "denied", None, None, None, path)
        entry, matched_root = selected
        workspace_id = str(entry.get("workspace_id") or "")
        role = str(entry.get("role") or "forbidden")
        if not bool(entry.get("enabled", True)):
            return self._decision("denied", "workspace_disabled", permission_name, "denied", workspace_id, role, matched_root, path)
        value = self.permission_value(entry, permission_name)
        if value == "allowed":
            return self._decision("allowed", "permission_allowed", permission_name, value, workspace_id, role, matched_root, path)
        if value == "ask":
            return self._decision("approval_required", "permission_requires_approval", permission_name, value, workspace_id, role, matched_root, path)
        return self._decision("denied", "permission_denied", permission_name, value, workspace_id, role, matched_root, path)

    def permission_for_action(self, action: str) -> PermissionName:
        if action in ALL_PERMISSIONS:
            return action  # type: ignore[return-value]
        return ACTION_PERMISSION_ALIASES.get(str(action), "script_execution")

    def permission_value(self, entry: dict[str, Any], permission: PermissionName) -> PermissionValue:
        role = str(entry.get("role") or "forbidden")
        defaults = self.role_defaults().get(role, ROLE_DEFAULTS["forbidden"])
        overrides = entry.get("permissions", {}) or {}
        value = str(overrides.get(permission, defaults.get(permission, "denied")))
        return value if value in {"allowed", "ask", "denied"} else "denied"  # type: ignore[return-value]

    def add_or_update_workspace(self, entry: WorkspaceEntry) -> dict[str, Any]:
        registry = dict(self.config)
        workspaces = [dict(item) for item in registry.get("workspaces", []) or [] if isinstance(item, dict)]
        payload = entry.model_dump()
        replaced = False
        for index, item in enumerate(workspaces):
            if str(item.get("workspace_id")) == entry.workspace_id:
                workspaces[index] = {**item, **payload}
                replaced = True
                break
        if not replaced:
            workspaces.append(payload)
        registry["workspaces"] = workspaces
        errors = self.validate_registry(registry)
        if errors:
            raise ValueError(";".join(errors))
        return registry

    def set_enabled(self, workspace_id: str, enabled: bool) -> dict[str, Any]:
        registry = dict(self.config)
        workspaces = [dict(item) for item in registry.get("workspaces", []) or [] if isinstance(item, dict)]
        for item in workspaces:
            if str(item.get("workspace_id")) == workspace_id:
                item["enabled"] = enabled
                registry["workspaces"] = workspaces
                return registry
        raise ValueError("workspace_not_found")

    def set_permissions(self, workspace_id: str, permissions: dict[str, str]) -> dict[str, Any]:
        registry = dict(self.config)
        workspaces = [dict(item) for item in registry.get("workspaces", []) or [] if isinstance(item, dict)]
        for item in workspaces:
            if str(item.get("workspace_id")) == workspace_id:
                item["permissions"] = {**(item.get("permissions", {}) or {}), **permissions}
                registry["workspaces"] = workspaces
                errors = self.validate_registry(registry)
                if errors:
                    raise ValueError(";".join(errors))
                return registry
        raise ValueError("workspace_not_found")

    def write_registry(self, registry: dict[str, Any]) -> None:
        errors = self.validate_registry(registry)
        if errors:
            raise ValueError(";".join(errors))
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(yaml.safe_dump(registry, sort_keys=False, allow_unicode=True), encoding="utf-8")
        self._config = registry

    def list_workspaces(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.config.get("workspaces", []) or [] if isinstance(item, dict)]

    def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        for item in self.list_workspaces():
            if str(item.get("workspace_id")) == workspace_id:
                return item
        return None

    def _select_workspace(self, path: str, *, registry: dict[str, Any] | None = None) -> tuple[dict[str, Any], str] | None:
        payload = registry or self.config
        normalized_path = self._normalize(path)
        matches: list[tuple[int, int, dict[str, Any], str]] = []
        restrictiveness = {
            "forbidden": 70,
            "protected": 60,
            "source_readonly": 50,
            "external_inbox": 45,
            "target_mutable": 40,
            "artifact_output": 35,
            "temp_staging": 30,
            "system_mutable": 20,
        }
        for entry in payload.get("workspaces", []) or []:
            if not isinstance(entry, dict):
                continue
            root = str(entry.get("root_path") or "")
            if root and self._is_under(normalized_path, root):
                role = str(entry.get("role") or "forbidden")
                matches.append((len(self._normalize(root)), restrictiveness.get(role, 70), entry, root))
        if not matches:
            return None
        _length, _restrictiveness, entry, root = sorted(matches, key=lambda item: (item[0], item[1]), reverse=True)[0]
        return entry, root

    def _decision(
        self,
        status: str,
        reason_code: str,
        permission: PermissionName,
        value: PermissionValue,
        workspace_id: str | None,
        role: str | None,
        root_path: str | None,
        target_path: str | None,
    ) -> WorkspacePermissionDecision:
        return WorkspacePermissionDecision(
            status=status,  # type: ignore[arg-type]
            reason_code=reason_code,
            permission=permission,
            permission_value=value,
            workspace_id=workspace_id,
            workspace_role=role,  # type: ignore[arg-type]
            root_path=root_path,
            target_path=target_path,
            trace=[
                {
                    "event_type": "runtime_permission_decision",
                    "status": status,
                    "reason_code": reason_code,
                    "permission": permission,
                    "permission_value": value,
                    "workspace_id": workspace_id,
                    "workspace_role": role,
                    "source": str(self.registry_path),
                }
            ],
        )

    def _normalize(self, value: str) -> str:
        return os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))

    def _is_under(self, normalized_path: str, root: str) -> bool:
        normalized_root = self._normalize(root)
        return normalized_path == normalized_root or normalized_path.startswith(normalized_root + os.sep)

    def workspace_id_for_path(self, root_path: str) -> str:
        leaf = Path(root_path).name or "workspace"
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in leaf).strip("_")
        return safe or "workspace"

    def status(self) -> dict[str, object]:
        errors = self.validate_registry()
        return {
            "status": "ok" if not errors else "degraded",
            "service": "workspace_permission_matrix",
            "workspaces": len(self.list_workspaces()),
            "permissions": len(ALL_PERMISSIONS),
            "errors": errors,
        }

