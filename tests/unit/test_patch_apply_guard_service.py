from aipinho.schemas.patching.apply.patch_apply_request import PatchApplyRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.patching.apply.patch_apply_guard_service import PatchApplyGuardService
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from patch_fixtures import patch_request, patch_workspace


def test_patch_apply_guard_allows_happy_path(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    quality = PatchQualityGateService().validate_plan(plan.plan_id)
    approval = PatchApplyService().request_approval(plan.plan_id)
    ApprovalService().approve(approval.approval_id)
    guard = PatchApplyGuardService().validate(plan, quality, PatchApplyRequest(approval_id=approval.approval_id, operator_confirmed=True))
    assert guard.allowed is True


def test_patch_apply_guard_blocks_operator_missing(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    quality = PatchQualityGateService().validate_plan(plan.plan_id)
    approval = PatchApplyService().request_approval(plan.plan_id)
    ApprovalService().approve(approval.approval_id)
    guard = PatchApplyGuardService().validate(plan, quality, PatchApplyRequest(approval_id=approval.approval_id, operator_confirmed=False))
    assert guard.allowed is False
    assert "operator_confirmation_required" in guard.blocking_reasons


def test_patch_apply_guard_blocks_snapshot_mismatch(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    quality = PatchQualityGateService().validate_plan(plan.plan_id)
    approval = PatchApplyService().request_approval(plan.plan_id)
    ApprovalService().approve(approval.approval_id)
    (workspace / "docs" / "note.md").write_text("# Changed\n", encoding="utf-8")
    guard = PatchApplyGuardService().validate(plan, quality, PatchApplyRequest(approval_id=approval.approval_id, operator_confirmed=True))
    assert guard.allowed is False
    assert any(reason.startswith("stale_snapshot:") for reason in guard.blocking_reasons)
