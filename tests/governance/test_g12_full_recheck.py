from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_g12_direct_and_persistent_chat_share_canonical_lifecycle() -> None:
    client = _client()
    direct = client.post(
        "/api/v1/chat",
        json={"message": "Somente planejamento textual. Nao escrever arquivos. product_planning_readonly", "context": {"surface": "api"}},
    )
    assert direct.status_code == 200
    assert direct.json()["governance_lifecycle"]["intent"]["intent_type"] == "product_planning_readonly"

    session = client.post("/api/v1/chat/sessions", json={"title": "g12"}).json()["session"]["session_id"]
    persistent = client.post(
        f"/api/v1/chat/sessions/{session}/send",
        json={"role": "user", "content": "Liste os workspaces aprovados para escrita.", "metadata": {}},
    )
    assert persistent.status_code == 200
    payload = persistent.json()["chat_response"]
    assert payload["governance_lifecycle"]["intent"]["intent_type"] == "workspace_permission_list"
    assert payload["governance_lifecycle"]["operation_contract"]["source_channel"] == "persistent_chat"


def test_g12_continue_openai_route_uses_canonical_lifecycle() -> None:
    response = _client().post(
        "/v1/chat/completions",
        json={
            "model": "aipinho-local",
            "stream": False,
            "messages": [{"role": "user", "content": "Liste os workspaces aprovados para escrita."}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    lifecycle = payload["aipinho"]["governance_lifecycle"]
    assert lifecycle["intent"]["intent_type"] == "workspace_permission_list"
    assert lifecycle["operation_contract"]["source_channel"] == "vscode_continue"


def test_g12_unknown_model_still_returns_structured_error() -> None:
    response = _client().post(
        "/v1/chat/completions",
        json={"model": "missing-model", "stream": False, "messages": [{"role": "user", "content": "ola"}]},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "model_not_found"
