from artifact_fixtures import approved_artifact_preview
from aipinho.services.artifacts.artifact_overwrite_policy_service import ArtifactOverwritePolicyService


def test_overwrite_policy_requires_snapshot_and_explicit_overwrite(tmp_path):
    _, _, _, preview, _ = approved_artifact_preview(tmp_path, allow_overwrite=True)
    service = ArtifactOverwritePolicyService()
    blocked, _ = service.validate(preview, allow_overwrite=False, current_existing_hash=preview.metadata["existing_target_hash"])
    assert "overwrite_requires_explicit_approval" in blocked
    blocked, _ = service.validate(preview, allow_overwrite=True, current_existing_hash="changed")
    assert "existing_file_changed_since_preview" in blocked
