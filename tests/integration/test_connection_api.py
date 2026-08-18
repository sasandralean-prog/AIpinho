from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def test_connection_api_profiles_select_test_and_adb():
    profiles = client.get("/api/v1/connection/profiles")
    assert profiles.status_code == 200
    assert {p["profile_id"] for p in profiles.json()["profiles"]} >= {"adb_reverse", "wifi_lan", "tailscale", "manual"}
    assert client.post("/api/v1/connection/profiles/select", json={"profile_id":"tailscale"}).json()["profile"]["profile_id"] == "tailscale"
    assert client.post("/api/v1/connection/test", json={"profile_id":"adb_reverse", "timeout_seconds":0.01}).status_code == 200
    commands = client.get("/api/v1/connection/adb/reverse-commands").json()["adb_reverse"]["commands"]
    assert "adb reverse tcp:9080 tcp:9080" in commands
    assert "adb reverse tcp:9099 tcp:9099" in commands
