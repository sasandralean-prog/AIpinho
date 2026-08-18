from tests.replay_regression_helpers import capture_snapshot

def test_capture_api_sanitizes_secret():
    snapshot=capture_snapshot("Bearer secretvalue")
    assert snapshot["sanitization"]["sanitized"] is True
    assert "secretvalue" not in str(snapshot)
