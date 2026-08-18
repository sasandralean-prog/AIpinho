from tests.replay_regression_helpers import client

def test_replay_status_api():
    body=client.get("/api/v1/replay/status").json()
    assert body["enabled"] is True
    assert body["side_effects_allowed"] is False
