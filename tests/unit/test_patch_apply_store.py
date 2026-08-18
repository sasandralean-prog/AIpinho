from aipinho.schemas.patching.apply.patch_apply_run import PatchApplyRun
from aipinho.services.patching.apply.patch_apply_event_service import PatchApplyEventService
from aipinho.services.patching.apply.patch_apply_store import PatchApplyStore


def test_patch_apply_store_save_get_run_events(tmp_path):
    store = PatchApplyStore(root=tmp_path / "apply")
    run = PatchApplyRun(apply_run_id="patch_apply_run_abcdef", plan_id="patch_plan_abcdef", quality_id="patch_quality_abcdef", approval_id="approval_abcdef", workspace="w", diff_hash="h", created_at="now", updated_at="now")
    store.save_run(run)
    event = PatchApplyEventService().create(run.apply_run_id, "created", "created")
    store.append_event(event)
    assert store.get_run(run.apply_run_id).plan_id == run.plan_id
    assert store.get_events(run.apply_run_id)[0].event_type == "created"
