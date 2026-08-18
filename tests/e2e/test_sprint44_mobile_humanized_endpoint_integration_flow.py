from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_sprint44_five_screen_flow_smoke():
    client = TestClient(create_app())
    for path in [
        "/api/v1/mobile/view-model/dashboard",
        "/api/v1/mobile/view-model/chat/chat_test",
        "/api/v1/mobile/view-model/pipeline",
        "/api/v1/mobile/view-model/debugger",
        "/api/v1/mobile/view-model/config",
    ]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["cards"]
        assert data["state"]["ui_decides_policy"] is False

