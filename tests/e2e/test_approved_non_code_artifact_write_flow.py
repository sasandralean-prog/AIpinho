from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.chat.chat_service import ChatService
from artifact_fixtures import approved_artifact_preview
from aipinho.schemas.artifacts.artifact_write_request import ArtifactWriteRequest
from aipinho.services.artifacts.artifact_write_execution_service import ArtifactWriteExecutionService
from aipinho.services.artifacts.artifact_write_store import ArtifactWriteStore


def test_approved_non_code_artifact_write_flow_and_chat_no_auto_write(tmp_path):
    workspace, preview_store, approval_store, preview, approval = approved_artifact_preview(tmp_path)
    execution = ArtifactWriteExecutionService(preview_store=preview_store, approval_store=approval_store, write_store=ArtifactWriteStore(root=tmp_path / "writes"))
    run = execution.create_run_from_preview(preview.preview_id, ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True))
    assert not (workspace / "reports" / "analysis.md").exists()
    result = execution.execute(run.write_run_id)
    assert result.status == "completed"
    assert result.post_write_validation.passed
    chat = ChatService().respond(ChatRequest(message="Salve agora"))
    assert chat.status == "preview"
    assert "chat_does_not_auto_write_files" in chat.warnings
