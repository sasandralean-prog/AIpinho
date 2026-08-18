from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_health_endpoint_returns_ok():
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status_endpoint_returns_200():
    client = TestClient(create_app())

    response = client.get("/api/v1/status")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_policy_status_endpoint_returns_200():
    client = TestClient(create_app())

    response = client.get("/api/v1/policy/status")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_routes_endpoint_returns_200():
    client = TestClient(create_app())

    response = client.get("/api/v1/routes")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
