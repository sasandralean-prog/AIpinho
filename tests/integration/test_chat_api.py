from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def _post(path: str, message: str):
    return client.post(path, json={"message": message, "context": {"surface": "api"}})


def test_post_chat_greeting_200():
    response = _post("/api/v1/chat", "Bom dia, tudo certo?")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert payload["intent"]["intent_type"] == "conversation"
    if payload["status"] == "degraded":
        assert "modelo leve" in payload["message"]


def test_post_chat_self_analysis_200():
    response = _post("/api/v1/chat", "Explique sua arquitetura atual")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["intent"]["intent_type"] == "self_analysis"
    assert "AIpinho" in payload["message"]


def test_post_chat_capability_200():
    response = _post("/api/v1/chat", "O que voce consegue fazer?")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["intent"]["intent_type"] == "capability_explanation"


def test_post_chat_permission_status_lists_configured_roots_without_task():
    response = _post(
        "/api/v1/chat",
        "Liste os diretorios que tem permissao para ler e escrever, incluindo artifact, patch, shell e network governado.",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["operation_type"] == "permission_status"
    assert payload["intent"]["intent_type"] == "permission_status"
    assert payload["intent"]["requires_task"] is False
    assert payload["intent"]["requires_workspace"] is False
    assert payload["task_id"] is None
    assert "C:\\Dev\\AIpinho" in payload["message"]
    assert "config/workspaces/workspace_registry.yaml" in payload["message"]


def test_post_chat_preview_patch_200():
    response = _post("/api/v1/chat/preview", r"Conserte o bug no projeto C:\Dev\AIpinho")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "preview"
    assert payload["intent"]["intent_type"] == "patch_request"
    assert payload["trace"]


def test_forbidden_root_returns_blocked_not_500():
    response = _post("/api/v1/chat", r"Corrija C:\Windows\System32")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["policy"]["safe_to_execute"] is False


def test_chat_status_200():
    response = client.get("/api/v1/chat/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_post_chat_invalid_session_id_returns_structured_error_not_500():
    response = client.post(
        "/api/v1/chat",
        json={"message": "oi", "session_id": "invalid-session", "context": {"surface": "api"}},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "invalid_session_id"


def test_post_chat_shell_request_creates_approval_without_execution():
    response = _post(
        "/api/v1/chat",
        r"Rode npm test no workspace C:\Users\rafae\Documents\AIpinhoTestes.",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending_approval"
    assert payload["operation_type"] == "governed_shell_request"
    assert payload["approval_id"].startswith("approval_")
    assert payload["policy"]["approval_required_for"] == ["run_command"]
    assert payload["policy"]["safe_to_execute"] is False
    assert "Nada foi executado" in payload["message"]
    operation_contract = payload["contract_preview"]["operation_contract"]
    assert operation_contract["source_channel"] == "chat"
    assert operation_contract["operation_type"] == "run_command"
    assert operation_contract["approval_required"] is True


def test_post_chat_write_request_creates_approval_without_execution():
    response = _post(
        "/api/v1/chat",
        r"Crie reports/sprint21_probe.md no workspace C:\Users\rafae\Documents\AIpinhoTestes com o texto probe sprint 21.",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending_approval"
    assert payload["operation_type"] == "governed_file_write"
    assert payload["approval_id"].startswith("approval_")
    assert payload["policy"]["approval_required_for"] == ["write_files"]
    assert payload["policy"]["safe_to_execute"] is False
    assert "Nenhum arquivo foi escrito" in payload["message"]
    operation_contract = payload["contract_preview"]["operation_contract"]
    assert operation_contract["source_channel"] == "chat"
    assert operation_contract["operation_type"] == "write_files"
    assert operation_contract["normalized_actions"] == ["create_file", "modify_file"]
