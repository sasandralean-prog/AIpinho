from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_config_view_model_exposes_capabilities_without_tokens():
    client = TestClient(create_app())

    response = client.get("/api/v1/mobile/view-model/config")

    assert response.status_code == 200
    data = response.json()
    assert data["capabilities"]["mobile_view_models_enabled"] is True
    assert data["capabilities"]["ui_decides_policy"] is False
    assert "token" not in str(data).lower() or "token_visible" in str(data)

