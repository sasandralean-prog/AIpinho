from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.memory.memory_candidate import MemoryCandidateScope
from aipinho.utils.yaml_loader import load_yaml_file


class MemoryCandidateScopeService:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_yaml_file(
            PATHS.config_root / "memory" / "memory_candidate_scope_policy.yaml",
            critical=True,
            root=PATHS.config_root / "memory",
        )

    def resolve(self, scope: MemoryCandidateScope | None, *, kind: str, text: str) -> MemoryCandidateScope:
        if scope is not None:
            return scope
        if kind == "user_instruction":
            return MemoryCandidateScope(scope_type="user_instruction", reason="explicit_user_instruction")
        if "policy" in text.lower() or kind == "policy_decision":
            return MemoryCandidateScope(scope_type="policy", reason="policy_claim")
        return MemoryCandidateScope(scope_type="", reason="missing_scope")

    def validate(self, scope: MemoryCandidateScope) -> list[str]:
        reasons: list[str] = []
        if not scope.scope_type:
            reasons.append("scope_missing")
        if scope.workspace and self._matches_any_root(scope.workspace, self._forbidden_roots()):
            reasons.append("forbidden_root_scope")
        return reasons

    def _forbidden_roots(self) -> list[str]:
        workspace = self.config.get("workspace", {}) if isinstance(self.config.get("workspace"), dict) else {}
        return [str(root) for root in workspace.get("forbidden_roots", []) or []]

    def _matches_any_root(self, path: str, roots: list[str]) -> bool:
        if not roots:
            return False
        normalized_path = self._normalize(path)
        for root in roots:
            normalized_root = self._normalize(root)
            if normalized_path == normalized_root or normalized_path.startswith(normalized_root.rstrip("\\/") + "\\"):
                return True
        return False

    def _normalize(self, path: str) -> str:
        return str(Path(path).expanduser().resolve(strict=False)).lower().replace("/", "\\").rstrip("\\")
