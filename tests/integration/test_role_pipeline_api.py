from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_role_pipeline_status_endpoint():
    response = client.get("/api/v1/role-pipelines/status")
    assert response.status_code == 200
    data = response.json()
    assert data["real_inference_auto_use"] is True
    assert data["tools_enabled"] is False
    assert data["write_enabled"] is False


def test_role_pipeline_preview_and_run_endpoints():
    payload = {"pipeline_id": "chat_basic", "user_message": "Ola", "intent_map": {"intent_type": "conversation"}, "policy_decision": {"status": "allowed"}, "model_mode": "deterministic"}
    preview = client.post("/api/v1/role-pipelines/preview", json=payload)
    assert preview.status_code == 200
    assert preview.json()["status"] == "preview"
    run = client.post("/api/v1/role-pipelines/run", json=payload)
    assert run.status_code == 200
    data = run.json()
    assert data["real_inference"] is False
    run_id = data["run"]["run_id"]
    assert client.get(f"/api/v1/role-pipelines/runs/{run_id}").status_code == 200
    assert client.get(f"/api/v1/role-pipelines/runs/{run_id}/trace").status_code == 200
