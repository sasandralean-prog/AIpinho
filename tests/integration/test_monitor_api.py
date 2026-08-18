from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def token_header():
    token = client.post("/api/v1/mobile/pairing/create-token").json()["pairing"]["token"]
    return {"Authorization": f"Bearer {token}"}

def test_monitor_api_status_ports_services_resources_restart_and_events():
    assert client.get("/api/v1/monitor/status").status_code == 200
    ports = client.get("/api/v1/monitor/ports").json()["ports"]
    assert {p["port"] for p in ports} == {9080, 9088, 9089, 9098, 9099}
    assert client.get("/api/v1/monitor/services").status_code == 200
    assert client.get("/api/v1/monitor/services/core_backend").json()["service"]["port"] == 9088
    assert client.get("/api/v1/monitor/resources").json()["resources"]["model_runtime_active"] is False
    restart = client.post("/api/v1/monitor/services/core_backend/restart", json={"requested_by":"test"}, headers=token_header())
    assert restart.status_code == 200
    assert restart.json()["restart"]["allowed"] is True
    blocked = client.post("/api/v1/monitor/ports/9099/restart", json={}, headers=token_header())
    assert blocked.json()["restart"]["allowed"] is False
    assert client.get("/api/v1/monitor/events").status_code == 200
