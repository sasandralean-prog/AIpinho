from __future__ import annotations

import os
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.services.security.path_guard_service import PathGuardService
from aipinho.utils.yaml_loader import load_yaml_file


class PatchTargetGuard:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "patch_target_policy.yaml", critical=True, root=PATHS.config_root / "patching")
        self.path_guard = PathGuardService()

    def validate(self, workspace: str, path: str) -> AffectedFile:
        decision = self.path_guard.validate_read_target(workspace, path)
        blocked = list(decision.violations)
        warnings = list(decision.warnings)
        normalized = decision.target_path or str(path)
        rel = self._relative(normalized, workspace)
        suffix = Path(normalized).suffix.lower()
        targets = self.policy.get("targets", {}) or {}
        allowed_exts = {str(item).lower() for item in targets.get("allowed_extensions", []) or []}
        blocked_exts = {str(item).lower() for item in targets.get("blocked_extensions", []) or []}
        blocked_dirs = [str(item).replace("\\", "/").lower().strip("/") for item in targets.get("blocked_dirs", []) or []]
        high_risk_dirs = [str(item).replace("\\", "/").lower().strip("/") for item in targets.get("high_risk_dirs", []) or []]
        allowed_roots = [str(item) for item in targets.get("allowed_roots", []) or []]
        forbidden_roots = [str(item) for item in targets.get("forbidden_roots", []) or []]
        rel_lower = rel.replace("\\", "/").lower().strip("/")
        if allowed_roots and not self._is_under_any(workspace, allowed_roots):
            blocked.append("workspace_root_not_allowed")
        if allowed_roots and not self._is_under_any(normalized, allowed_roots):
            blocked.append("target_root_not_allowed")
        if forbidden_roots and self._is_under_any(normalized, forbidden_roots):
            blocked.append("target_forbidden_root")
        if suffix in blocked_exts:
            blocked.append("blocked_extension")
        if suffix and suffix not in allowed_exts:
            blocked.append("extension_not_allowed")
        if any(rel_lower == item or rel_lower.startswith(item + "/") for item in blocked_dirs):
            blocked.append("blocked_directory")
        risk = "high" if any(rel_lower == item or rel_lower.startswith(item + "/") for item in high_risk_dirs) else "medium"
        if "protected_root" in blocked or "outside_workspace" in blocked or "path_traversal" in blocked or "blocked_extension" in blocked:
            risk = "critical"
        return AffectedFile(path=path, normalized_path=normalized, relative_path=rel, status="blocked" if blocked else "allowed", risk_level=risk, warnings=list(dict.fromkeys(warnings)), blocked_reasons=list(dict.fromkeys(blocked)))

    def _relative(self, target: str, workspace: str) -> str:
        try:
            return str(Path(target).resolve(strict=False).relative_to(Path(workspace).resolve(strict=False)))
        except Exception:
            return str(target)

    def _is_under_any(self, value: str, roots: list[str]) -> bool:
        try:
            normalized_value = os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))
        except Exception:
            return False
        for root in roots:
            try:
                normalized_root = os.path.normcase(str(Path(root).expanduser().resolve(strict=False)))
            except Exception:
                continue
            if normalized_value == normalized_root or normalized_value.startswith(normalized_root + os.sep):
                return True
        return False

    def status(self) -> dict[str, object]:
        targets = self.policy.get("targets", {}) or {}
        return {"status": "ok", "service": "patch_target_guard", "allowed_extensions": targets.get("allowed_extensions", []), "blocked_extensions": targets.get("blocked_extensions", []), "allowed_roots": targets.get("allowed_roots", [])}
