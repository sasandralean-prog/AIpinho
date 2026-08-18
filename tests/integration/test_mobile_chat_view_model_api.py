from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_chat_view_model_keeps_raw_hidden_by_default():
    client = TestClient(create_app())

    response = client.get("/api/v1/mobile/view-model/chat/chat_test")

    assert response.status_code == 200
    data = response.json()
    assert data["state"]["screen"] == "chat"
    assert data["state"]["raw_default_visible"] is False
    assert data["presentation"]["raw_default_visible"] is False
    assert "messages" in data["presentation"]
    assert "details" in data["presentation"]
    assert any(card["copy"]["summary_available"] for card in data["cards"])
