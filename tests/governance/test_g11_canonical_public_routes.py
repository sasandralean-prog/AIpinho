from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def _first_endpoint_module(path: str, method: str) -> str:
    app = create_app()
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set()) or set()
        if method.upper() in methods:
            return route.endpoint.__module__
    raise AssertionError(f"route not found: {method} {path}")


def test_g11_public_operational_routes_are_owned_by_canonical_router_first() -> None:
    assert _first_endpoint_module("/api/v1/chat", "POST").endswith("governance_lifecycle_router")
    assert _first_endpoint_module("/api/v1/chat/sessions/{session_id}/send", "POST").endswith("governance_lifecycle_router")
    assert _first_endpoint_module("/v1/chat/completions", "POST").endswith("governance_lifecycle_router")


def test_g11_lifecycle_status_reports_rewired_public_routes() -> None:
    response = _client().get("/api/v1/governance/lifecycle/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["source_of_truth"] == "GovernanceLifecycleSnapshot"
    assert "POST /api/v1/chat" in payload["public_routes_rewired"]
    assert "POST /v1/chat/completions" in payload["public_routes_rewired"]


def test_g11_chat_diagnostics_uses_canonical_inference_status() -> None:
    response = _client().get("/api/v1/chat/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    diagnostics = payload["legacy_content_provider"]
    assert diagnostics["dependencies"]["model_invocation"]["service"] == "model_invocation"
    assert diagnostics["dependencies"]["model_invocation"]["inference_runtime"]["service"] == "inference_runtime"
    assert "llama_cpp" in diagnostics["dependencies"]


def test_g11_direct_chat_response_contains_canonical_lifecycle() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={"message": "Somente planejamento textual. Nao escrever arquivos. Classifique como product_planning_readonly.", "context": {"surface": "api"}},
    )

    assert response.status_code == 200
    payload = response.json()
    lifecycle = payload["governance_lifecycle"]
    assert lifecycle["intent"]["intent_type"] == "product_planning_readonly"
    assert lifecycle["operation_contract"]["source_channel"] == "api_chat"
    assert payload["policy"]["canonical_lifecycle"]["state"] == lifecycle["state"]


def test_g11_persistent_chat_send_contains_canonical_lifecycle_in_chat_response() -> None:
    client = _client()
    session = client.post("/api/v1/chat/sessions", json={"title": "g11 route"}).json()["session"]["session_id"]
    response = client.post(
        f"/api/v1/chat/sessions/{session}/send",
        json={"role": "user", "content": "Liste os workspaces aprovados para escrita.", "metadata": {}},
    )

    assert response.status_code == 200
    payload = response.json()["chat_response"]
    lifecycle = payload["governance_lifecycle"]
    assert lifecycle["operation_contract"]["source_channel"] == "persistent_chat"
    assert "canonical_lifecycle" in payload["policy"]


def test_g11_continue_chat_completion_contains_canonical_lifecycle_metadata() -> None:
    response = _client().post(
        "/v1/chat/completions",
        json={
            "model": "aipinho-local",
            "stream": False,
            "messages": [{"role": "user", "content": "Responda apenas: AIpinho conectada."}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["content"].strip()
    assert payload["aipinho"]["route"] == "canonical_continue"
    assert payload["aipinho"]["governance_lifecycle"]["operation_contract"]["source_channel"] == "vscode_continue"
