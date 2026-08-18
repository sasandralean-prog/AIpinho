from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_preview import ArtifactPreview
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactOverwritePolicyService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_overwrite_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")

    def validate(self, preview: ArtifactPreview, *, allow_overwrite: bool, current_existing_hash: str | None) -> tuple[list[str], list[str]]:
        blocked: list[str] = []
        warnings: list[str] = []
        target_path = preview.target.normalized_target_path or preview.target.target_path
        target_exists = Path(target_path).exists()
        if target_exists and not allow_overwrite:
            blocked.append("overwrite_requires_explicit_approval")
        if allow_overwrite:
            if not preview.would_overwrite:
                blocked.append("overwrite_not_in_preview")
            expected_hash = str(preview.metadata.get("existing_target_hash") or "")
            if not expected_hash:
                blocked.append("existing_file_snapshot_missing")
            elif current_existing_hash and current_existing_hash != expected_hash:
                blocked.append("existing_file_changed_since_preview")
        if not target_exists and allow_overwrite:
            warnings.append("overwrite_requested_for_new_file")
        return list(dict.fromkeys(blocked)), list(dict.fromkeys(warnings))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_overwrite_policy", "backup_required": True}
