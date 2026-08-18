from aipinho.schemas.replay.contracts import ReplayCaptureRequest
from aipinho.services.replay.replay_capture_service import ReplayCaptureService
from aipinho.services.replay.replay_case_service import ReplayCaseService

def test_case_points_to_sanitized_snapshot():
    snapshot = ReplayCaptureService().capture(ReplayCaptureRequest(reason="unit")).snapshot
    case = ReplayCaseService().create(snapshot.metadata.snapshot_id, "unit")
    assert case.snapshot_id == snapshot.metadata.snapshot_id
