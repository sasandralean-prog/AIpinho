from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers import governance_lifecycle_router, public_runtime_api_router


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(governance_lifecycle_router.router)
    app.include_router(public_runtime_api_router.router)
    return app


def test_api_v1_chat_is_canonical_chat_request_route() -> None:
    client = TestClient(_app())

    response = client.post(
        "/api/v1/chat",
        json={
            "client_id": "public_runtime_shape",
            "client_type": "rest",
            "api_version": "1.0",
            "operation": "chat",
            "contract": {"contract_type": "conversation"},
            "payload": {},
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert any(item.get("loc") == ["body", "message"] and item.get("type") == "missing" for item in body.get("detail", []))


def test_public_runtime_chat_uses_explicit_runtime_route() -> None:
    client = TestClient(_app())

    response = client.post(
        "/api/v1/runtime/chat",
        json={
            "client_id": "public_runtime_shape",
            "client_type": "rest",
            "api_version": "1.0",
            "operation": "chat",
            "contract": {"contract_type": "conversation"},
            "payload": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["operation"] == "chat"
    assert response.json()["gateway_required"] is True


def test_no_duplicate_post_route_owns_api_v1_chat() -> None:
    app = _app()
    post_chat_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/chat"
        and "POST" in set(getattr(route, "methods", set()) or set())
    ]
    assert len(post_chat_routes) == 1
    assert post_chat_routes[0].endpoint.__name__ == "post_chat"

