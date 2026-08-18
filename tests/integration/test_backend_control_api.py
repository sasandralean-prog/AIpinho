from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.services.security.local_token_service import LocalTokenService


def test_backend_control_status_endpoint():
    client = TestClient(create_app())

    response = client.get("/api/v1/backend-control/status")

    assert response.status_code == 200
    assert response.json()["backend"]["control_port"] == 9099


def test_backend_control_restart_requires_token():
    client = TestClient(create_app())

    response = client.post("/api/v1/backend-control/restart", headers={"x-aipinho-served-port": "9099"})

    assert response.status_code == 401


def test_backend_control_restart_blocks_wrong_port_with_token():
    client = TestClient(create_app())
    token = LocalTokenService().create_token().token

    response = client.post(
        "/api/v1/backend-control/restart",
        headers={"Authorization": f"Bearer {token}", "x-aipinho-served-port": "9088"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert "backend_control_port_required" in response.json()["restart"]["blocked_reasons"]


def test_bootstrap_control_status_and_token_requirement():
    client = TestClient(create_app())

    status = client.get("/api/v1/bootstrap-control/status")
    blocked = client.post("/api/v1/bootstrap-control/monitor/restart")

    assert status.status_code == 200
    assert status.json()["bootstrap"]["bootstrap_port"] == 9080
    assert status.json()["bootstrap"]["controlled_port"] == 9099
    assert blocked.status_code == 401
