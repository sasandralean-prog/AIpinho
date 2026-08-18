from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_chat_reports_role_model_status_without_auto_inference():
    response = client.post("/api/v1/chat", json={"message": "Quais modelos por role estao configurados?", "context": {"surface": "api"}})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["real_inference"] is False
    assert "role" in data["message"].lower()
    assert "endpoint explicito" in data["message"].lower()


def test_chat_does_not_run_role_model_when_user_asks_to_execute():
    response = client.post("/api/v1/chat", json={"message": "Rode o modelo da role coder com Qwen 7B agora", "context": {"surface": "api"}})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "preview"
    assert data["real_inference"] is False
    assert "chat_does_not_run_role_models" in data["warnings"]


def test_chat_blocks_14b_role_model_without_manual_endpoint():
    response = client.post("/api/v1/chat", json={"message": "Use 14B na role coder agora", "context": {"surface": "api"}})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["real_inference"] is False
    assert "large_model_manual_only" in data["warnings"]
