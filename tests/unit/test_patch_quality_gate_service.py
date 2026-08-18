from aipinho.schemas.patching.quality.patch_quality_gate_request import PatchQualityGateRequest
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from patch_fixtures import patch_request, patch_workspace


def test_patch_quality_gate_passes_safe_static_plan_without_write(tmp_path):
    workspace = patch_workspace(tmp_path)
    before = (workspace / "docs" / "note.md").read_text(encoding="utf-8")
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    result = PatchQualityGateService().validate_plan(plan.plan_id)
    assert result is not None
    assert result.status in {"passed", "passed_with_warnings"}
    assert result.apply_enabled is True
    assert result.write_enabled is True
    assert result.safe_for_future_apply_review is True
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before


def test_patch_quality_gate_rejects_stale_snapshot(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    (workspace / "docs" / "note.md").write_text("# Changed outside preview\n", encoding="utf-8")
    result = PatchQualityGateService().validate_plan(plan.plan_id)
    assert result is not None
    assert result.status in {"failed", "rejected"}
    assert result.safe_for_future_apply_review is False
    assert any(finding.category in {"target_snapshot", "hunk_validation"} for finding in result.findings)


def test_patch_quality_gate_validate_diff_rejects_policy_bypass():
    diff = "--- a/config.yaml\n+++ b/config.yaml\n@@ -1 +1 @@\n-apply_enabled: false\n+apply_enabled: true\n"
    result = PatchQualityGateService().validate_diff(PatchQualityGateRequest(diff_text=diff))
    assert result.status == "rejected"
    assert result.apply_enabled is False
