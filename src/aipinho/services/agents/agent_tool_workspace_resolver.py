from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import WorkspaceResolution
from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.services.policy_kernel.mission_local_resource_scope_service import MissionLocalResourceScopeService
from aipinho.utils.yaml_loader import load_yaml_file


class AgentToolWorkspaceResolver:
    def __init__(
        self,
        path: Path | None = None,
        *,
        root: Path | None = None,
        mission_scopes: MissionLocalResourceScopeService | None = None,
    ) -> None:
        self.path = path or PATHS.config_root / "agents" / "tool_gateway_workspaces.yaml"
        self.root = root or PATHS.config_root
        self.mission_scopes = mission_scopes or MissionLocalResourceScopeService()

    def _data(self) -> dict[str, Any]:
        return load_yaml_file(self.path, critical=False, root=self.root)

    def _entries(self) -> list[dict[str, Any]]:
        entries = self._data().get("workspaces", [])
        if not isinstance(entries, list):
            return []
        normalized: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("enabled", True):
                continue
            root_path = entry.get("root")
            if not root_path:
                continue
            try:
                resolved = Path(str(root_path)).expanduser().resolve()
            except OSError:
                continue
            normalized.append({**entry, "resolved_root": resolved})
        return normalized

    def resolve(
        self,
        *,
        workspace_id: str | None = None,
        path_ref: str | None = None,
        relative_path: str | None = None,
        access: str = "read",
        local_resources: list[MissionResourceScope] | None = None,
    ) -> WorkspaceResolution:
        entries = self._entries()
        selected: dict[str, Any] | None = None
        mission_scope: MissionResourceScope | None = None
        explicit_path = path_ref
        if not explicit_path and relative_path:
            try:
                relative_candidate = Path(relative_path).expanduser()
                if relative_candidate.is_absolute():
                    explicit_path = str(relative_candidate)
            except OSError:
                explicit_path = None

        if workspace_id:
            selected = next(
                (entry for entry in entries if str(entry.get("workspace_id")) == workspace_id),
                None,
            )
            if selected is None:
                mission_scope = self.mission_scopes.resource_by_id(
                    local_resources,
                    workspace_id,
                )
        if selected is None and mission_scope is None and explicit_path:
            candidate_path = Path(explicit_path).expanduser().resolve()
            matches = [
                entry
                for entry in entries
                if self._is_relative_to(candidate_path, entry["resolved_root"])
            ]
            matches.sort(key=lambda entry: len(str(entry["resolved_root"])), reverse=True)
            selected = matches[0] if matches else None
            if selected is None:
                mission_scope = self.mission_scopes.scope_for_path(
                    local_resources,
                    str(candidate_path),
                )

        if selected is None and mission_scope is not None and mission_scope.locator:
            root_path = Path(mission_scope.locator).expanduser().resolve()
            selected = {
                "workspace_id": mission_scope.resource_id,
                "role": str(mission_scope.role or "source_readonly"),
                "resolved_root": root_path,
                "mission_resource": True,
            }
        if selected is None:
            reason = "workspace_id_not_registered" if workspace_id else "workspace_unknown"
            return WorkspaceResolution(
                workspace_id=workspace_id,
                allowed=False,
                reason_code=reason,
            )

        role = str(selected.get("role", "unknown"))
        root_path: Path = selected["resolved_root"]
        resolved_path = self._resolve_child(
            root_path,
            path_ref=path_ref,
            relative_path=relative_path,
        )
        if resolved_path is None:
            return WorkspaceResolution(
                workspace_id=str(selected.get("workspace_id")),
                workspace_role=role,  # type: ignore[arg-type]
                root_path_sanitized=str(root_path),
                allowed=False,
                reason_code="path_traversal_or_outside_workspace",
            )

        deny_match = self._deny_override(entries, resolved_path)
        if deny_match is not None:
            return WorkspaceResolution(
                workspace_id=str(deny_match.get("workspace_id")),
                workspace_role=str(deny_match.get("role", "forbidden")),  # type: ignore[arg-type]
                root_path_sanitized=str(deny_match["resolved_root"]),
                resolved_path_sanitized=str(resolved_path),
                allowed=False,
                reason_code="workspace_deny_override",
                evidence_refs=[f"workspace:{deny_match.get('workspace_id')}"] ,
            )

        allowed = self._role_allows(role, access)
        reason = (
            "workspace_allowed"
            if allowed
            else "source_readonly_write_denied"
            if role == "source_readonly" and access in {"write", "shell"}
            else f"{role}_does_not_allow_{access}"
        )
        refs = [f"workspace:{selected.get('workspace_id')}"]
        if selected.get("mission_resource"):
            refs.append("authority:mission_contract.local_resources")
        return WorkspaceResolution(
            workspace_id=str(selected.get("workspace_id")),
            workspace_role=role,  # type: ignore[arg-type]
            root_path_sanitized=str(root_path),
            resolved_path_sanitized=str(resolved_path),
            allowed=allowed,
            reason_code=reason,
            evidence_refs=refs,
        )

    def _resolve_child(self, root_path: Path, *, path_ref: str | None, relative_path: str | None) -> Path | None:
        try:
            if relative_path:
                relative = Path(relative_path)
                if relative.is_absolute():
                    candidate = relative.expanduser().resolve()
                else:
                    candidate = (root_path / relative).resolve()
            elif path_ref:
                candidate = Path(path_ref).expanduser().resolve()
            else:
                candidate = root_path.resolve()
        except OSError:
            return None
        if not self._is_relative_to(candidate, root_path):
            return None
        return candidate

    def _deny_override(self, entries: list[dict[str, Any]], path: Path) -> dict[str, Any] | None:
        denied = [
            entry
            for entry in entries
            if str(entry.get("role")) in {"forbidden", "protected"} and self._is_relative_to(path, entry["resolved_root"])
        ]
        denied.sort(key=lambda entry: len(str(entry["resolved_root"])), reverse=True)
        return denied[0] if denied else None

    def _role_allows(self, role: str, access: str) -> bool:
        if role in {"forbidden", "protected", "unknown"}:
            return False
        if access == "read":
            return role in {"source_readonly", "target_mutable", "system_mutable"}
        if access == "write":
            return role in {"target_mutable", "system_mutable"}
        if access == "shell":
            return role in {"target_mutable", "system_mutable"}
        return False

    def _is_relative_to(self, path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
