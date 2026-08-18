from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def test_realtime_api_status_heartbeat_stream():
    assert client.get("/api/v1/realtime/status").json()["port"] == 9089
    assert client.get("/api/v1/realtime/heartbeat").json()["status"] == "ok"
    with client.stream("GET", "/api/v1/realtime/events/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
