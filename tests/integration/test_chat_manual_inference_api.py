from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_chat_model_status_endpoint_reports_safe_defaults():
    response = client.get("/api/v1/chat/model-status")
    assert response.status_code == 200
    data = response.json()
    assert data["normal_chat_real_inference"] is False
    assert data["manual_chat_inference_enabled"] is False


def test_manual_inference_preview_blocked_by_default_and_no_process():
    response = client.post("/api/v1/chat/manual-inference/preview", json={"message": "Ola"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["process_started"] is False
    assert data["real_inference"] is False


def test_manual_inference_blocked_by_default_and_no_process():
    response = client.post("/api/v1/chat/manual-inference", json={"message": "Ola", "allow_real_inference": True, "operator_confirmed": True})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["process_started"] is False
    assert data["real_inference"] is False


def test_normal_chat_endpoint_remains_no_real_inference():
    response = client.post("/api/v1/chat", json={"message": "Ola"})
    assert response.status_code == 200
    data = response.json()
    assert data["real_inference"] is False
