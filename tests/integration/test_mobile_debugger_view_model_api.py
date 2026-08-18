from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_debugger_view_model_is_read_only_and_has_filters():
    client = TestClient(create_app())

    response = client.get("/api/v1/mobile/view-model/debugger")

    assert response.status_code == 200
    data = response.json()
    assert data["state"]["screen"] == "debugger"
    assert data["state"]["ui_decides_policy"] is False
    assert "raw_sanitized" in data["filters"]

