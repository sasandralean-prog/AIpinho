from aipinho.schemas.patching.apply import (
    HunkApplyResult,
    PatchApplyBackup,
    PatchApplyEvent,
    PatchApplyFileResult,
    PatchApplyGuardResult,
    PatchApplyRequest,
    PatchApplyResult,
    PatchApplyRun,
    PostApplyValidation,
    RollbackResult,
)


def test_patch_apply_contracts_validate():
    request = PatchApplyRequest(approval_id="approval_abcdef", operator_confirmed=True)
    guard = PatchApplyGuardResult(status="allowed", allowed=True)
    run = PatchApplyRun(apply_run_id="patch_apply_run_abcdef", plan_id="patch_plan_abcdef", quality_id="patch_quality_abcdef", approval_id="approval_abcdef", workspace="w", diff_hash="h", guard=guard, created_at="now", updated_at="now")
    event = PatchApplyEvent(event_id="patch_apply_event_abcdef", apply_run_id=run.apply_run_id, event_type="created", created_at="now", summary="x")
    backup = PatchApplyBackup(backup_id="patch_backup_abcdef", apply_run_id=run.apply_run_id, file_path="a", backup_path="b", original_hash="h", created_at="now")
    hunk = HunkApplyResult(hunk_id="h", file_path="a", status="applied", applied=True)
    file_result = PatchApplyFileResult(file_path="a", status="completed", hunk_results=[hunk])
    validation = PostApplyValidation(status="passed", passed=True)
    rollback = RollbackResult()
    result = PatchApplyResult(apply_run_id=run.apply_run_id, plan_id=run.plan_id, status="completed", files=[file_result], post_apply_validation=validation, rollback=rollback, created_at="now", updated_at="now")
    assert request.operator_confirmed is True
    assert event.apply_run_id == run.apply_run_id
    assert backup.backup_id.startswith("patch_backup_")
    assert result.safe_to_report_success is False
