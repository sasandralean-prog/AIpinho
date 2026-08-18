from __future__ import annotations

import os
from pathlib import Path

from aipinho.schemas.artifacts.artifact_target import ArtifactTarget, ArtifactTargetValidation
from aipinho.services.artifacts.artifact_target_policy_service import ArtifactTargetPolicyService
from aipinho.services.artifacts.artifact_trace_service import ArtifactTraceService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.security.path_guard_service import PathGuardService


SOURCE_CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rs", ".cpp", ".h", ".hpp", ".cs"}
SCRIPT_EXTENSIONS = {".sh", ".ps1", ".bat", ".cmd"}


class ArtifactPathGuardService:
    def __init__(self, policy: ArtifactTargetPolicyService | None = None) -> None:
        self.policy = policy or ArtifactTargetPolicyService()
        self.path_guard = PathGuardService()
        self.workspace_policy = WorkspacePolicyService().load()
        self.trace = ArtifactTraceService()

    def validate(self, workspace: str, target_path: str) -> ArtifactTargetValidation:
        blocked: list[str] = []
        warnings: list[str] = []
        trace = []
        raw = str(target_path or "")
        workspace_policy = self.workspace_policy.evaluate(workspace_path=workspace, requires_workspace=True)
        workspace_allowed = not workspace_policy.blocked and bool(workspace)
        if not workspace_allowed:
            blocked.append("forbidden_root" if workspace_policy.blocked else "workspace_required")
        if workspace and not self._under_allowed_workspace_root(Path(workspace)):
            blocked.append("workspace_root_not_allowed")
        if raw.startswith("\\\\") or raw.startswith("//"):
            blocked.append("unc_path_blocked")
        if raw.startswith("\\\\.") or raw.startswith("\\\\?"):
            blocked.append("device_path_blocked")
        parts = [part for part in raw.replace("\\", "/").split("/") if part]
        path_traversal = ".." in parts
        if path_traversal:
            blocked.append("path_traversal")
        try:
            workspace_path = Path(workspace).expanduser().resolve(strict=False)
            target = self.path_guard.resolve_target_path(workspace, raw)
            normalized = str(target)
            target_relative = self._relative_text(target, workspace_path)
        except Exception as exc:
            target = Path(raw)
            normalized = raw
            target_relative = raw
            blocked.append("path_resolution_failed")
            warnings.append(str(exc))
        outside_workspace = not self.path_guard.is_within_workspace(target, workspace) if workspace else True
        if outside_workspace:
            blocked.append("outside_workspace")
        if not self._under_allowed_workspace_root(target):
            blocked.append("target_root_not_allowed")
        forbidden_root = self._under_forbidden_root(target) or self._under_forbidden_root(Path(workspace))
        if forbidden_root:
            blocked.append("forbidden_root")
        extension = target.suffix.lower()
        allowed_exts = set(self.policy.allowed_extensions())
        blocked_exts = set(self.policy.blocked_extensions())
        extension_allowed = bool(extension and extension in allowed_exts and extension not in blocked_exts)
        if not extension_allowed:
            blocked.append("extension_not_allowed" if extension not in blocked_exts else "blocked_extension")
        rel_norm = target_relative.replace("\\", "/").strip("/")
        rel_lower = rel_norm.lower()
        base_dir = self._base_dir(rel_lower)
        base_dir_allowed = self._starts_with_any(rel_lower, self.policy.allowed_base_dirs()) and not self._starts_with_any(rel_lower, self.policy.blocked_base_dirs())
        if not base_dir_allowed:
            blocked.append("base_dir_not_allowed")
        source_code_target = extension in SOURCE_CODE_EXTENSIONS or rel_lower.startswith("src/") or rel_lower.startswith("tests/")
        if source_code_target:
            blocked.append("source_code_target")
        config_mutation_target = rel_lower.startswith("config/")
        if config_mutation_target:
            blocked.append("config_mutation_target")
        script_target = extension in SCRIPT_EXTENSIONS or rel_lower.startswith("scripts/")
        if script_target:
            blocked.append("script_target")
        would_overwrite = target.exists()
        trace.append(self.trace.item("artifact_path_guard", "checked", "target_policy_applied", source="config/artifacts/artifact_target_policy.yaml", data={"target": normalized, "blocked": blocked}))
        unique = list(dict.fromkeys(blocked))
        artifact_target = ArtifactTarget(workspace=str(workspace), target_path=raw, normalized_target_path=normalized, relative_target_path=rel_norm, extension=extension, base_dir=base_dir)
        return ArtifactTargetValidation(
            valid=not unique,
            workspace_allowed=workspace_allowed,
            target_allowed=not unique,
            extension_allowed=extension_allowed,
            base_dir_allowed=base_dir_allowed,
            forbidden_root=forbidden_root,
            path_traversal=path_traversal,
            outside_workspace=outside_workspace,
            would_overwrite=would_overwrite,
            source_code_target=source_code_target,
            config_mutation_target=config_mutation_target,
            script_target=script_target,
            blocked_reasons=unique,
            warnings=list(dict.fromkeys(warnings)),
            trace=trace,
            target=artifact_target,
        )

    def _under_forbidden_root(self, path: Path) -> bool:
        path_norm = os.path.normcase(str(path.resolve(strict=False)))
        for root in self.policy.forbidden_roots():
            root_norm = os.path.normcase(str(Path(root).resolve(strict=False)))
            if path_norm == root_norm or path_norm.startswith(root_norm + os.sep):
                return True
        return False

    def _under_allowed_workspace_root(self, path: Path) -> bool:
        roots = self.policy.allowed_workspace_roots()
        if not roots:
            return True
        path_norm = os.path.normcase(str(path.resolve(strict=False)))
        for root in roots:
            root_norm = os.path.normcase(str(Path(root).resolve(strict=False)))
            if path_norm == root_norm or path_norm.startswith(root_norm + os.sep):
                return True
        return False

    def _relative_text(self, target: Path, workspace: Path) -> str:
        try:
            return str(target.resolve(strict=False).relative_to(workspace.resolve(strict=False)))
        except ValueError:
            return str(target)

    def _base_dir(self, rel_lower: str) -> str:
        parts = [part for part in rel_lower.split("/") if part]
        if len(parts) >= 2 and f"{parts[0]}/{parts[1]}" in self.policy.allowed_base_dirs():
            return f"{parts[0]}/{parts[1]}"
        return parts[0] if parts else ""

    def _starts_with_any(self, rel_lower: str, prefixes: list[str]) -> bool:
        return any(rel_lower == prefix or rel_lower.startswith(prefix + "/") for prefix in prefixes)

    def status(self) -> dict[str, object]:
        policy_status = self.policy.status()
        return {"status": policy_status.get("status", "ok"), "service": "artifact_path_guard", "policy": policy_status}
