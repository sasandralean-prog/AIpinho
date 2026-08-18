from aipinho.schemas.replay.contracts import ReplayCaptureRequest
from aipinho.services.replay.replay_capture_service import ReplayCaptureService

def test_capture_creates_sanitized_snapshot():
    result = ReplayCaptureService().capture(ReplayCaptureRequest(reason="unit", prompt="Bearer secretvalue"))
    assert result.status == "created"
    assert result.snapshot.sanitization.sanitized is True
    assert "secretvalue" not in str(result.snapshot.model_dump())
