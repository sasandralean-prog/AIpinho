from artifact_fixtures import artifact_workspace
from aipinho.services.artifacts.artifact_diff_preview_service import ArtifactDiffPreviewService
from aipinho.services.artifacts.artifact_path_guard_service import ArtifactPathGuardService


def test_artifact_diff_preview_service_new_existing_and_secret(tmp_path):
    workspace = artifact_workspace(tmp_path)
    guard = ArtifactPathGuardService()
    service = ArtifactDiffPreviewService()
    assert service.preview(guard.validate(str(workspace), "reports/new.md"), "new").diff_type == "new_file"
    (workspace / "reports" / "existing.md").write_text("old", encoding="utf-8")
    diff = service.preview(guard.validate(str(workspace), "reports/existing.md"), "new")
    assert diff.target_exists is True
    assert diff.available is True
    (workspace / "reports" / "secret.md").write_text("api_key=abc123", encoding="utf-8")
    assert "existing_target_secret_not_read" in service.preview(guard.validate(str(workspace), "reports/secret.md"), "new").warnings
