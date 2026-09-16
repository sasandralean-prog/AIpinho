from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import WorkspaceResolution
from aipinho.services.governance.intent_workspace_scope_service import IntentWorkspaceScopeService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.utils.yaml_loader import load_yaml_file


class AgentToolWorkspaceResolver:
    def __init__(
        self,
        path: Path | None = None,
        *,
        root: Path | None = None,
        intent_scopes: IntentWorkspaceScopeService | None = None,
        workspace_policy: WorkspacePolicyService | None = None,
    ) -> None:
        self.path = path or PATHS.config_root / "agents" / "tool_gateway_workspaces.yaml"
        self.root = root or PATHS.config_root
        self.intent_scopes = intent_scopes or IntentWorkspaceScopeService()
        self.workspace_policy = workspace_policy or WorkspacePolicyService().load()

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
        workspace_scope_contract: dict[str, Any] | None = None,
    ) -> WorkspaceResolution:
        entries = self._entries()
        dynamic = self._resolve_intent_scope(
            entries=entries,
            workspace_scope_contract=workspace_scope_contract,
            path_ref=path_ref,
            relative_path=relative_path,
            access=access,
        )
        if dynamic is not None:
            return dynamic
        selected: dict[str, Any] | None = None
        if workspace_id:
            selected = next((entry for entry in entries if str(entry.get("workspace_id")) == workspace_id), None)
            if selected is None:
                return WorkspaceResolution(workspace_id=workspace_id, allowed=False, reason_code="workspace_id_not_registered")
        else:
            candidate_path = Path(path_ref).expanduser().resolve() if path_ref else None
            if candidate_path is not None:
                matches = [entry for entry in entries if self._is_relative_to(candidate_path, entry["resolved_root"])]
                matches.sort(key=lambda entry: len(str(entry["resolved_root"])), reverse=True)
                selected = matches[0] if matches else None
        if selected is None:
            return WorkspaceResolution(workspace_id=workspace_id, allowed=False, reason_code="workspace_unknown")

        role = str(selected.get("role", "unknown"))
        root_path: Path = selected["resolved_root"]
        resolved_path = self._resolve_child(root_path, path_ref=path_ref, relative_path=relative_path)
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
                evidence_refs=[f"workspace:{deny_match.get('workspace_id')}"],
            )

        allowed = self._role_allows(role, access)
        reason = "workspace_allowed" if allowed else ("source_readonly_write_denied" if role == "source_readonly" and access == "write" else f"{role}_does_not_allow_{access}")
        return WorkspaceResolution(
            workspace_id=str(selected.get("workspace_id")),
            workspace_role=role,  # type: ignore[arg-type]
            root_path_sanitized=str(root_path),
            resolved_path_sanitized=str(resolved_path),
            allowed=allowed,
            reason_code=reason,
            evidence_refs=[f"workspace:{selected.get('workspace_id')}"],
        )

    def _resolve_intent_scope(
        self,
        *,
        entries: list[dict[str, Any]],
        workspace_scope_contract: dict[str, Any] | None,
        path_ref: str | None,
        relative_path: str | None,
        access: str,
    ) -> WorkspaceResolution | None:
        if not isinstance(workspace_scope_contract, dict) or not workspace_scope_contract:
            return None
        candidate_text = path_ref or relative_path
        if not candidate_text:
            candidate_text = str(
                workspace_scope_contract.get("primary_workspace") or ""
            )
        if not candidate_text:
            return None
        scope = self.intent_scopes.scope_for_path(
            contract=workspace_scope_contract,
            path=candidate_text,
        )
        if scope is None:
            return WorkspaceResolution(
                allowed=False,
                reason_code="intent_workspace_scope_not_matched",
            )
        root_path = Path(str(scope.get("path") or "")).expanduser().resolve()
        resolved_path = self._resolve_child(
            root_path,
            path_ref=path_ref,
            relative_path=relative_path,
        )
        if resolved_path is None:
            return WorkspaceResolution(
                workspace_id=str(scope.get("scope_id") or ""),
                workspace_role=str(scope.get("role") or "unknown"),
                root_path_sanitized=str(root_path),
                allowed=False,
                reason_code="path_traversal_or_outside_workspace",
            )
        deny_match = self._deny_override(entries, resolved_path)
        if deny_match is not None:
            return WorkspaceResolution(
                workspace_id=str(deny_match.get("workspace_id")),
                workspace_role=str(deny_match.get("role", "forbidden")),
                root_path_sanitized=str(deny_match["resolved_root"]),
                resolved_path_sanitized=str(resolved_path),
                allowed=False,
                reason_code="workspace_deny_override",
                evidence_refs=[f"workspace:{deny_match.get('workspace_id')}"],
            )
        restrictive = self._restrictive_static_match(entries, resolved_path)
        if restrictive is not None and access in {"write", "shell"}:
            return WorkspaceResolution(
                workspace_id=str(restrictive.get("workspace_id")),
                workspace_role=str(restrictive.get("role", "source_readonly")),
                root_path_sanitized=str(restrictive["resolved_root"]),
                resolved_path_sanitized=str(resolved_path),
                allowed=False,
                reason_code="registered_readonly_scope_overrides_prompt_mutation",
                evidence_refs=[f"workspace:{restrictive.get('workspace_id')}"],
            )
        policy = self.workspace_policy.evaluate(
            workspace_path=str(root_path),
            requires_workspace=True,
        )
        if policy.blocked:
            return WorkspaceResolution(
                workspace_id=str(scope.get("scope_id") or ""),
                workspace_role=str(scope.get("role") or "unknown"),
                root_path_sanitized=str(root_path),
                resolved_path_sanitized=str(resolved_path),
                allowed=False,
                reason_code="workspace_protected_root",
            )
        role = str(scope.get("role") or "unknown")
        allowed = self._role_allows(role, access)
        return WorkspaceResolution(
            workspace_id=str(scope.get("scope_id") or ""),
            workspace_role=role,
            root_path_sanitized=str(root_path),
            resolved_path_sanitized=str(resolved_path),
            allowed=allowed,
            reason_code=(
                "workspace_allowed_by_intent_scope"
                if allowed
                else f"{role}_does_not_allow_{access}"
            ),
            evidence_refs=[f"intent_scope:{scope.get('scope_id')}"],
        )

    def _restrictive_static_match(
        self,
        entries: list[dict[str, Any]],
        path: Path,
    ) -> dict[str, Any] | None:
        matches = [
            entry
            for entry in entries
            if str(entry.get("role")) in {"source_readonly", "external_inbox"}
            and self._is_relative_to(path, entry["resolved_root"])
        ]
        matches.sort(key=lambda entry: len(str(entry["resolved_root"])), reverse=True)
        return matches[0] if matches else None

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
