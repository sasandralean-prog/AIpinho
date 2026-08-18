from aipinho.schemas.patching.apply.patch_apply_request import PatchApplyRequest
from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.patching.apply.patch_apply_engine import PatchApplyEngine
from aipinho.services.patching.apply.workspace_mutation_tracker import WorkspaceMutationTracker
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from aipinho.services.session.session_store import utc_now
from patch_fixtures import patch_request, patch_workspace


def _approved_plan(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    quality = PatchQualityGateService().validate_plan(plan.plan_id)
    service = PatchApplyService()
    approval = service.request_approval(plan.plan_id)
    ApprovalService().approve(approval.approval_id)
    return workspace, plan, quality, approval, service


def test_patch_apply_service_create_run_does_not_write(tmp_path):
    workspace, plan, _quality, approval, service = _approved_plan(tmp_path)
    before = (workspace / "docs" / "note.md").read_text(encoding="utf-8")
    run = service.create_run_from_plan(plan.plan_id, PatchApplyRequest(approval_id=approval.approval_id, operator_confirmed=True))
    assert run.status == "ready_to_execute"
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before


def test_patch_apply_service_execute_valid_patch_with_post_validation(tmp_path):
    workspace, plan, _quality, approval, service = _approved_plan(tmp_path)
    run = service.create_run_from_plan(plan.plan_id, PatchApplyRequest(approval_id=approval.approval_id, operator_confirmed=True))
    result = service.execute(run.apply_run_id)
    assert result is not None
    assert result.status == "completed"
    assert result.safe_to_report_success is True
    assert result.post_apply_validation.passed is True
    assert result.files[0].backup_id
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == "# New\n"


def test_patch_apply_service_executes_approved_new_text_file(tmp_path):
    workspace = patch_workspace(tmp_path)
    service = PatchApplyService()
    request = patch_request(workspace, path="docs/new.md", objective="Crie um arquivo de texto aprovado.")
    request.replacements = {"docs/new.md": "# Created"}
    plan = PatchPlanningService().create_plan(request).plan
    quality = PatchQualityGateService().validate_plan(plan.plan_id)
    assert quality is not None and quality.status == "passed"
    approval = service.request_approval(plan.plan_id)
    ApprovalService().approve(approval.approval_id)
    run = service.create_run_from_plan(plan.plan_id, PatchApplyRequest(approval_id=approval.approval_id, operator_confirmed=True))
    result = service.execute(run.apply_run_id)
    assert result is not None
    assert result.status == "completed"
    assert result.safe_to_report_success is True
    assert result.files[0].backup_id is None
    assert "created_new_file" in result.files[0].warnings
    assert (workspace / "docs" / "new.md").read_text(encoding="utf-8") == "# Created"


def test_patch_apply_service_blocks_missing_approval(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    PatchQualityGateService().validate_plan(plan.plan_id)
    run = PatchApplyService().create_run_from_plan(plan.plan_id, PatchApplyRequest(operator_confirmed=True))
    assert run.status == "blocked"
    assert "approval_required" in run.blocked_reasons


def test_patch_apply_service_duplicate_execute_returns_existing_result(tmp_path):
    _workspace, plan, _quality, approval, service = _approved_plan(tmp_path)
    run = service.create_run_from_plan(plan.plan_id, PatchApplyRequest(approval_id=approval.approval_id, operator_confirmed=True))
    first = service.execute(run.apply_run_id)
    second = service.execute(run.apply_run_id)
    assert first is not None and second is not None
    assert first.created_at == second.created_at


def test_patch_apply_engine_matches_nested_paths_with_mixed_separators(tmp_path):
    target = tmp_path / "src" / "main" / "kotlin" / "Main.kt"
    plan = PatchPlan(
        plan_id="patch_plan_nested",
        status="needs_review",
        workspace=str(tmp_path),
        affected_files=[
            AffectedFile(
                path="src\\main\\kotlin\\Main.kt",
                relative_path="src\\main\\kotlin\\Main.kt",
                normalized_path=str(target),
            )
        ],
        hunks=[
            PatchHunk(
                hunk_id="hunk_nested",
                file_path="src/main/kotlin/Main.kt",
                original="",
                replacement="fun main() = println(\"ok\")\n",
            )
        ],
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    result = PatchApplyEngine().apply(plan, "patch_apply_run_nested", WorkspaceMutationTracker([str(target)]))

    assert result[0].status == "completed"
    assert result[0].changed is True
    assert result[0].hunk_results and result[0].hunk_results[0].applied is True
    assert target.read_text(encoding="utf-8") == "fun main() = println(\"ok\")\n"
