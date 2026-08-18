from __future__ import annotations

import difflib
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_diff_preview import ArtifactDiffPreview
from aipinho.schemas.artifacts.artifact_target import ArtifactTargetValidation
from aipinho.services.artifacts.artifact_secret_scanner import ArtifactSecretScanner
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactDiffPreviewService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_diff_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        self.secret_scanner = ArtifactSecretScanner()

    def preview(self, target: ArtifactTargetValidation, new_content: str) -> ArtifactDiffPreview:
        if target.target is None or not target.target.normalized_target_path:
            return ArtifactDiffPreview(available=False, diff_type="none", warnings=["target_unavailable"])
        path = Path(target.target.normalized_target_path)
        if not path.exists():
            return ArtifactDiffPreview(available=True, target_exists=False, diff_type="new_file", old_summary=None, new_summary=self._summary(new_content), diff_preview=None)
        if not path.is_file():
            return ArtifactDiffPreview(available=False, target_exists=True, diff_type="none", warnings=["target_not_file"])
        max_bytes = int((self.policy.get("diff", {}) or {}).get("max_existing_file_bytes", 200000))
        if path.stat().st_size > max_bytes:
            return ArtifactDiffPreview(available=False, target_exists=True, diff_type="overwrite_text", warnings=["existing_target_too_large"])
        try:
            old_content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ArtifactDiffPreview(available=False, target_exists=True, diff_type="overwrite_text", warnings=["existing_target_binary_or_non_utf8"])
        if self.secret_scanner.has_secret(old_content):
            return ArtifactDiffPreview(available=False, target_exists=True, diff_type="overwrite_text", warnings=["existing_target_secret_not_read"])
        diff = "\n".join(difflib.unified_diff(old_content.splitlines(), new_content.splitlines(), fromfile="existing", tofile="preview", lineterm=""))
        max_chars = int((self.policy.get("diff", {}) or {}).get("max_diff_chars", 20000))
        truncated = len(diff) > max_chars
        return ArtifactDiffPreview(available=True, target_exists=True, diff_type="overwrite_text", old_summary=self._summary(old_content), new_summary=self._summary(new_content), diff_preview=diff[:max_chars], truncated=truncated)

    def _summary(self, content: str) -> str:
        return f"{len(content)} chars, {len(content.encode('utf-8', errors='replace'))} bytes"

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_diff_preview", "read_only": True}
