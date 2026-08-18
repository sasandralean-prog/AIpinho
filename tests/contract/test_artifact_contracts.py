from artifact_fixtures import artifact_workspace, preview_request
from aipinho.schemas.artifacts.artifact_draft import ArtifactDraftRequest
from aipinho.schemas.artifacts.artifact_source import ArtifactSource
from aipinho.services.artifacts.artifact_writer_preview_service import ArtifactWriterPreviewService
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore


def test_artifact_contracts_validate(tmp_path):
    workspace = artifact_workspace(tmp_path)
    request = ArtifactDraftRequest(workspace=str(workspace), target_path="reports/a.md", source=ArtifactSource(content="ok"))
    assert request.source.source_type == "user_provided_content"
    service = ArtifactWriterPreviewService(store=ArtifactPreviewStore(root=tmp_path / "store"))
    preview = service.create_preview(preview_request(workspace))
    assert preview.validation.target.valid is True
    assert preview.validation.content.valid is True
    assert preview.risk.approval_required is True
    assert preview.diff.diff_type == "new_file"
