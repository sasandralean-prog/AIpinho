from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.patching.apply.patch_apply_request import PatchApplyRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from aipinho.services.validation.validation_gate_service import ValidationGateService
from patch_fixtures import patch_request, patch_workspace


def test_approved_patch_apply_controlled_mutation_flow(tmp_path):
    workspace = patch_workspace(tmp_path)
    before = (workspace / "docs" / "note.md").read_text(encoding="utf-8")
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    quality = PatchQualityGateService().validate_plan(plan.plan_id)
    assert quality.status == "passed"
    service = PatchApplyService()
    approval = service.request_approval(plan.plan_id)
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before
    ApprovalService().approve(approval.approval_id)
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before
    run = service.create_run_from_plan(plan.plan_id, PatchApplyRequest(approval_id=approval.approval_id, operator_confirmed=True))
    assert run.status == "ready_to_execute"
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before
    result = service.execute(run.apply_run_id)
    assert result.status == "completed"
    assert result.post_apply_validation.passed is True
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == "# New\n"
    side_effect = ValidationGateService().validate_side_effects({
        "side_effect_type": "patch_apply",
        "apply_run_id": run.apply_run_id,
        "status": "completed",
        "approval_scope": "patch_apply",
        "quality_status": "passed",
        "post_apply_validation_passed": True,
        "unexpected_writes": [],
    })
    assert side_effect.status in {"passed", "passed_with_warnings"}
    chat = ChatService().respond(ChatRequest(message="Aplique o patch aprovado"))
    assert chat.status == "blocked"
    assert "chat_auto_apply_disabled" in chat.warnings
