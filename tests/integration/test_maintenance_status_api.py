from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def test_status_api():
    body = client.get("/api/v1/maintenance/status").json()
    assert body["enabled"] is True
    assert body["autonomous_apply"] is False
