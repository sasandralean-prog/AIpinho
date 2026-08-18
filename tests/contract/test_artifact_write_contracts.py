from aipinho.schemas.artifacts.artifact_post_write_validation import ArtifactPostWriteValidation
from aipinho.schemas.artifacts.artifact_write_backup import ArtifactWriteBackup
from aipinho.schemas.artifacts.artifact_write_event import ArtifactWriteEvent
from aipinho.schemas.artifacts.artifact_write_request import ArtifactWriteRequest
from aipinho.schemas.artifacts.artifact_write_result import ArtifactWriteResult
from aipinho.schemas.artifacts.artifact_write_run import ArtifactWriteRun


def test_artifact_write_contracts_validate_minimal_payloads():
    ArtifactWriteRequest(preview_id="p", approval_id="a", operator_confirmed=True)
    ArtifactWriteRun(write_run_id="artifact_write_run_abcdef", preview_id="p", approval_id="a", workspace="w", target_path="reports/a.md", created_at="now", updated_at="now")
    ArtifactWriteEvent(event_id="e", write_run_id="artifact_write_run_abcdef", event_type="created", created_at="now")
    ArtifactWriteBackup(backup_id="b", write_run_id="artifact_write_run_abcdef", original_path="a", backup_path="b", original_hash="h", created_at="now")
    ArtifactPostWriteValidation()
    ArtifactWriteResult(write_run_id="artifact_write_run_abcdef", preview_id="p", approval_id="a", status="blocked", target_path="reports/a.md", created_at="now")
