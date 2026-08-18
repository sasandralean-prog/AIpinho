from aipinho.schemas.replay.contracts import ReplayCaptureRequest
from aipinho.services.replay.replay_capture_service import ReplayCaptureService
from aipinho.services.replay.replay_case_service import ReplayCaseService
from aipinho.services.replay.replay_runner_service import ReplayRunnerService

def test_runner_is_dry_run_with_no_side_effects():
    snapshot = ReplayCaptureService().capture(ReplayCaptureRequest(reason="unit")).snapshot
    case = ReplayCaseService().create(snapshot.metadata.snapshot_id, "unit")
    run = ReplayRunnerService().run(case.case_id)
    assert run.dry_run is True
    assert run.side_effects_performed is False
    assert run.patch_apply_executed is False
