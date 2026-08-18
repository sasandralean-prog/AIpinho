from artifact_fixtures import artifact_workspace
from aipinho.schemas.artifacts.artifact_draft import ArtifactDraftRequest
from aipinho.schemas.artifacts.artifact_source import ArtifactSource
from aipinho.services.artifacts.artifact_draft_service import ArtifactDraftService
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore


def test_artifact_draft_service_create_and_block_missing_source(tmp_path):
    workspace = artifact_workspace(tmp_path)
    service = ArtifactDraftService(ArtifactPreviewStore(root=tmp_path / "store"))
    draft = service.create_draft(ArtifactDraftRequest(workspace=str(workspace), target_path="reports/a.md", source=ArtifactSource(content="ok")))
    assert draft.status == "draft"
    assert service.get_draft(draft.draft_id) is not None
    blocked = service.create_draft(ArtifactDraftRequest(workspace=str(workspace), target_path="", source=ArtifactSource()))
    assert blocked.status == "blocked"
