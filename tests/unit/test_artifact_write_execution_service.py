from artifact_fixtures import approved_artifact_preview
from aipinho.schemas.artifacts.artifact_write_request import ArtifactWriteRequest
from aipinho.services.artifacts.artifact_write_execution_service import ArtifactWriteExecutionService
from aipinho.services.artifacts.artifact_write_store import ArtifactWriteStore


def service(tmp_path, preview_store, approval_store):
    return ArtifactWriteExecutionService(preview_store=preview_store, approval_store=approval_store, write_store=ArtifactWriteStore(root=tmp_path / "writes"))


def test_create_run_from_approved_preview_does_not_write(tmp_path):
    workspace, preview_store, approval_store, preview, approval = approved_artifact_preview(tmp_path)
    execution = service(tmp_path, preview_store, approval_store)
    run = execution.create_run_from_preview(preview.preview_id, ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True))
    assert run.status == "ready_to_execute"
    assert not (workspace / "reports" / "analysis.md").exists()


def test_execute_new_file_and_duplicate_execute(tmp_path):
    workspace, preview_store, approval_store, preview, approval = approved_artifact_preview(tmp_path)
    execution = service(tmp_path, preview_store, approval_store)
    run = execution.create_run_from_preview(preview.preview_id, ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True))
    result = execution.execute(run.write_run_id)
    assert result.status == "completed"
    assert result.post_write_validation.passed is True
    assert result.safe_to_report_success is True
    assert (workspace / "reports" / "analysis.md").exists()
    duplicate = execution.execute(run.write_run_id)
    assert duplicate == result


def test_execute_overwrite_with_backup(tmp_path):
    workspace, preview_store, approval_store, preview, approval = approved_artifact_preview(tmp_path, allow_overwrite=True)
    execution = service(tmp_path, preview_store, approval_store)
    request = ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True, allow_overwrite=True)
    run = execution.create_run_from_preview(preview.preview_id, request)
    assert run.status == "ready_to_execute"
    result = execution.execute(run.write_run_id)
    assert result.status == "completed"
    assert result.backup_id
    assert (workspace / "reports" / "analysis.md").read_text(encoding="utf-8").startswith("# Report")


def test_cancel_blocks_later_execute(tmp_path):
    _, preview_store, approval_store, preview, approval = approved_artifact_preview(tmp_path)
    execution = service(tmp_path, preview_store, approval_store)
    run = execution.create_run_from_preview(preview.preview_id, ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True))
    cancelled = execution.cancel(run.write_run_id)
    assert cancelled.status == "cancelled"
    result = execution.execute(run.write_run_id)
    assert result.status == "blocked"
    assert "write_run_not_ready:cancelled" in result.blocked_reasons
