from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_mobile_view_model_status_api():
    client = TestClient(create_app())

    response = client.get("/api/v1/mobile/view-model/status")

    assert response.status_code == 200
    data = response.json()
    assert data["mobile_view_models_enabled"] is True
    assert data["ui_decides_policy"] is False
    assert data["raw_default_visible"] is False

