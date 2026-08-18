from patch_fixtures import patch_request, patch_workspace
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.patching.patch_planning_service import PatchPlanningService


def test_patch_plan_store_roundtrip(tmp_path):
    workspace = patch_workspace(tmp_path)
    store = PatchPlanStore(root=tmp_path / "patch_store")
    plan = PatchPlanningService(store=store).create_plan(patch_request(workspace)).plan
    assert store.get_plan(plan.plan_id).plan_id == plan.plan_id
    assert store.get_diff(plan.plan_id) is not None
    assert store.get_evidence(plan.plan_id)
    assert store.get_risk(plan.plan_id) is not None
    assert store.get_trace(plan.plan_id)
