from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def test_event_status_includes_maintenance_contracts():
    body=client.get("/api/v1/events/status").json()
    assert body["status"]=="ok"
    assert body["contracts_loaded"] >= 49
