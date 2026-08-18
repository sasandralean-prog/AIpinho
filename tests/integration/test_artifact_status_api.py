from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def test_artifact_status_api_and_workspace_direct_download_blocked():
    status = client.get("/api/v1/artifacts/status")
    assert status.status_code == 200
    assert status.json()["service"]["port"] == 9098
    assert client.get("/api/v1/artifacts/links/policy").json()["direct_workspace_serve_enabled"] is False
    blocked = client.get("/api/v1/artifacts/some-file/download")
    assert blocked.status_code == 401
    assert blocked.json()["detail"] == "local_token_required"
