from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.services.validation.validation_common import as_dict, finding
from aipinho.utils.yaml_loader import load_yaml_file


_PATH_KEYS = {
    "path",
    "file_path",
    "source_path",
    "target_path",
    "resolved_path",
    "canonical_path",
    "workspace",
    "workspace_path",
    "project_root",
    "cwd",
    "working_directory",
}
_PATH_LIST_KEYS = {
    "paths",
    "source_paths",
    "target_paths",
    "allowed_roots",
    "external_roots",
    "library_roots",
}
_STRUCTURED_CONTEXT_KEYS = {
    "workspace_snapshot",
    "workspace_context",
    "execution_context",
    "retrieval_context",
    "bootstrap_context",
    "path_guard",
    "path_guard_decision",
    "access",
}


class WorkspaceAccessValidator:
    def __init__(self) -> None:
        self.policy = load_yaml_file(
            PATHS.config_root / "validation" / "workspace_access_validation_policy.yaml",
            critical=True,
            root=PATHS.config_root / "validation",
        )
        self.forbidden = [
            str(item).lower().rstrip("\\/")
            for item in self.policy.get("forbidden_roots", []) or []
        ]

    def validate(self, payload: Any) -> list:
        data = as_dict(payload)
        findings = []
        operational_paths = self._operational_paths(data)
        normalized = [self._normalize(item) for item in operational_paths]
        for root in self.forbidden:
            if any(self._under_root(item, root) for item in normalized):
                findings.append(
                    finding(
                        "forbidden_root_access",
                        "Forbidden root access",
                        f"Operational access references forbidden root: {root}",
                        severity="critical",
                        validator="workspace_access",
                        evidence=[root],
                        blocking=True,
                    )
                )
        if any(self._has_traversal(item) for item in operational_paths):
            findings.append(
                finding(
                    "path_traversal_signal",
                    "Path traversal signal",
                    "An operational path contains a traversal marker.",
                    severity="error",
                    validator="workspace_access",
                    evidence=[".."],
                    blocking=True,
                )
            )
        snapshot = data.get("workspace_snapshot") if isinstance(data, dict) else None
        if isinstance(snapshot, dict):
            if snapshot.get("blocked") is True:
                findings.append(
                    finding(
                        "workspace_blocked",
                        "Workspace blocked",
                        str(snapshot.get("reason") or "workspace snapshot says blocked"),
                        severity="error",
                        validator="workspace_access",
                        blocking=True,
                    )
                )
            if snapshot.get("needs_clarification") is True:
                findings.append(
                    finding(
                        "workspace_needs_clarification",
                        "Workspace needs clarification",
                        "Workspace snapshot requires clarification.",
                        severity="warning",
                        validator="workspace_access",
                    )
                )
        return findings

    def _operational_paths(self, data: dict[str, Any]) -> list[str]:
        paths: list[str] = []
        self._collect_named_paths(data, paths, top_level=True)
        events = data.get("events")
        if isinstance(events, list):
            for event in events:
                if not isinstance(event, dict):
                    continue
                self._collect_named_paths(event, paths)
                metadata = event.get("metadata")
                if isinstance(metadata, dict):
                    self._collect_named_paths(metadata, paths, recurse=True)
        return list(dict.fromkeys(item for item in paths if item))
    def _collect_named_paths(
        self,
        value: dict[str, Any],
        paths: list[str],
        *,
        top_level: bool = False,
        recurse: bool = False,
    ) -> None:
        for key, item in value.items():
            key_text = str(key).casefold()
            if key_text in _PATH_KEYS or key_text.endswith("_path"):
                self._append_values(paths, item)
                continue
            if key_text in _PATH_LIST_KEYS or key_text.endswith("_paths"):
                self._append_values(paths, item)
                continue
            if key_text in _STRUCTURED_CONTEXT_KEYS and isinstance(item, dict):
                self._collect_named_paths(item, paths, recurse=True)
                continue
            if recurse and isinstance(item, dict):
                self._collect_named_paths(item, paths, recurse=True)
        if top_level:
            for key in ("workspace", "path", "file_path"):
                self._append_values(paths, value.get(key))

    @staticmethod
    def _append_values(paths: list[str], value: Any) -> None:
        if isinstance(value, str):
            if value.strip():
                paths.append(value.strip())
            return
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    paths.append(item.strip())

    @staticmethod
    def _normalize(value: str) -> str:
        return value.casefold().replace("/", "\\").rstrip("\\/")

    @staticmethod
    def _under_root(value: str, root: str) -> bool:
        normalized_root = root.casefold().replace("/", "\\").rstrip("\\/")
        return value == normalized_root or value.startswith(normalized_root + "\\")

    @staticmethod
    def _has_traversal(value: str) -> bool:
        normalized = value.replace("/", "\\")
        return "..\\" in normalized or normalized == ".."

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "workspace_access_validator"}
