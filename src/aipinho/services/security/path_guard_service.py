from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.security.sandbox_decision import SandboxDecision
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.utils.yaml_loader import load_yaml_file


class PathGuardService:
    RESERVED_NAMES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}

    def __init__(self, config_path: Path | None = None, workspace_policy: WorkspacePolicyService | None = None, secret_guard: SecretGuardService | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "security" / "path_guard_policy.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.workspace_policy = workspace_policy or WorkspacePolicyService().load()
        self.secret_guard = secret_guard or SecretGuardService()

    @property
    def policy(self) -> dict[str, object]:
        value = self.config.get("path_guard", {})
        return value if isinstance(value, dict) else {}

    def normalize_path(self, path: str | Path) -> str:
        resolved = Path(path).expanduser().resolve(strict=False)
        text = str(resolved)
        if self.policy.get("normalize_case_on_windows", True):
            return os.path.normcase(text)
        return text

    def resolve_target_path(self, workspace: str, path: str) -> Path:
        workspace_path = Path(workspace).expanduser().resolve(strict=False)
        raw_path = Path(path).expanduser()
        if raw_path.is_absolute():
            return raw_path.resolve(strict=False)
        return (workspace_path / raw_path).resolve(strict=False)

    def is_within_workspace(self, target: str | Path, workspace: str | Path) -> bool:
        target_norm = self.normalize_path(target)
        workspace_norm = self.normalize_path(workspace)
        try:
            return os.path.commonpath([target_norm, workspace_norm]) == workspace_norm
        except ValueError:
            return False

    def is_protected_root(self, path: str | Path) -> bool:
        return self.is_protected_for_read(path)

    def is_protected_for_read(self, path: str | Path) -> bool:
        for protected in self.workspace_policy.config.get("protected_roots", []) or []:
            if not isinstance(protected, dict):
                continue
            protected_path = str(protected.get("path") or "")
            if not protected_path:
                continue
            if self.workspace_policy._is_under(str(path), protected_path):
                return bool(protected.get("block_read", True) or protected.get("requires_governed_approval", False))
        return False

    def is_secret_path(self, path: str | Path) -> bool:
        name = Path(path).name.lower()
        if self.secret_guard.is_secret_path(path):
            return True
        return any(isinstance(pattern, str) and fnmatch.fnmatch(name, pattern.lower()) for pattern in self.config.get("protected_patterns", []) or [])

    def is_allowed_extension(self, path: str | Path) -> bool:
        allowed = [str(item).lower() for item in self.config.get("allowed_extensions_for_text_read", []) or []]
        suffix = Path(path).suffix.lower()
        if not suffix:
            return True
        return suffix in allowed

    def is_blocked_extension(self, path: str | Path) -> bool:
        blocked = [str(item).lower() for item in self.config.get("blocked_extensions", []) or []]
        return Path(path).suffix.lower() in blocked

    def validate_read_target(self, workspace: str | None, path: str | None) -> SandboxDecision:
        violations: list[str] = []
        warnings: list[str] = []
        trace: list[dict[str, object]] = []
        if not workspace:
            return SandboxDecision(status="invalid", allowed=False, reason="workspace_required", violations=["workspace_required"])
        if not path:
            return SandboxDecision(status="invalid", allowed=False, reason="path_required", workspace=workspace, violations=["path_required"])

        raw_path = str(path)
        workspace_policy = self.workspace_policy.evaluate(workspace_path=workspace, requires_workspace=True)
        if workspace_policy.blocked or self.is_protected_for_read(workspace):
            violations.append("protected_root")
            trace.append({"stage": "path_guard", "rule": "workspace_read_policy", "decision": "blocked", "reason": workspace_policy.reason})

        if self.policy.get("block_unc_paths", True) and (raw_path.startswith("\\\\") or raw_path.startswith("//")):
            violations.append("unc_path_blocked")
        if self.policy.get("block_device_paths", True) and (raw_path.startswith("\\\\.") or raw_path.startswith("\\\\?")):
            violations.append("device_path_blocked")
        if self.policy.get("block_relative_escape", True) and ".." in set(Path(raw_path).parts):
            violations.append("path_traversal")
        if self.policy.get("block_reserved_names", True) and Path(raw_path).stem.lower() in self.RESERVED_NAMES:
            violations.append("reserved_name")

        try:
            workspace_path = Path(workspace).expanduser().resolve(strict=False)
            target_path = self.resolve_target_path(workspace, raw_path)
        except Exception as exc:
            return SandboxDecision(status="invalid", allowed=False, reason="path_resolution_failed", workspace=workspace, target_path=raw_path, violations=["path_resolution_failed"], warnings=[str(exc)])

        normalized_workspace = self.normalize_path(workspace_path)
        normalized_target = self.normalize_path(target_path)
        if not self.is_within_workspace(target_path, workspace_path):
            violations.append("outside_workspace")
        if self.is_protected_root(target_path):
            violations.append("protected_root")
        if self.is_secret_path(target_path):
            violations.append("secret_file")
        if self.is_blocked_extension(target_path):
            violations.append("blocked_extension")
        if target_path.exists() and target_path.is_file() and not self.is_allowed_extension(target_path):
            violations.append("extension_not_allowed")
        if self.policy.get("block_symlink_escape", True) and target_path.exists() and target_path.is_symlink():
            real_target = target_path.resolve(strict=True)
            if not self.is_within_workspace(real_target, workspace_path):
                violations.append("symlink_escape")

        unique_violations = list(dict.fromkeys(violations))
        if unique_violations:
            return SandboxDecision(status="blocked", allowed=False, reason=unique_violations[0], workspace=str(workspace_path), target_path=str(target_path), normalized_workspace=normalized_workspace, normalized_target_path=normalized_target, violations=unique_violations, warnings=warnings, trace=trace)
        return SandboxDecision(status="allowed", allowed=True, reason="path_allowed", workspace=str(workspace_path), target_path=str(target_path), normalized_workspace=normalized_workspace, normalized_target_path=normalized_target, warnings=warnings, trace=trace)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "path_guard", "blocked_extensions": len(self.config.get("blocked_extensions", []) or []), "protected_patterns": len(self.config.get("protected_patterns", []) or [])}
