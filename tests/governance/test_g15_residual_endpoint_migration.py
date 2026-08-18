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


def test_vscode_action_preview_is_owned_by_canonical_router_first() -> None:
    assert _first_endpoint_module("/v1/integrations/vscode/actions/preview", "POST").endswith("governance_lifecycle_router")
    assert _first_endpoint_module("/v1/integrations/vscode/actions/execute", "POST").endswith("governance_lifecycle_router")
    assert _first_endpoint_module("/api/v1/chat/manual-inference/preview", "POST").endswith("governance_lifecycle_router")
    assert _first_endpoint_module("/api/v1/chat/manual-inference", "POST").endswith("governance_lifecycle_router")
    assert _first_endpoint_module("/api/v1/chat/status", "GET").endswith("governance_lifecycle_router")


def test_vscode_action_preview_uses_canonical_lifecycle_and_creates_approval() -> None:
    response = _client().post(
        "/v1/integrations/vscode/actions/preview",
        json={
            "workspace_path": r"C:\Users\rafae\Documents\AIpinhoTestes",
            "action_type": "create_directory",
            "target_paths": [r"C:\Users\rafae\Documents\AIpinhoTestes\G15Preview"],
            "source": "vscode_continue",
            "reason": "g15 test",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["canonical_route"] is True
    assert payload["status"] == "pending_approval"
    assert payload["approval_id"].startswith("approval_")
    assert payload["governance_lifecycle"]["operation_contract"]["source_channel"] == "vscode_continue_action_preview"
    assert payload["governance_lifecycle"]["policy"]["permission"] == "ask"


def test_vscode_action_execute_requires_approval_id_and_does_not_directly_execute() -> None:
    response = _client().post(
        "/v1/integrations/vscode/actions/execute",
        json={"source": "vscode_continue"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["reason_code"] == "continue_execute_requires_approval_id"


def test_workspace_query_endpoint_stays_canonical_readonly() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={"message": "Liste os workspaces aprovados para escrita.", "context": {"surface": "api"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["operation_type"] == "workspace_permission_list"
    assert payload["approval_id"] is None
    assert payload["governance_lifecycle"]["intent"]["intent_type"] == "workspace_permission_list"
