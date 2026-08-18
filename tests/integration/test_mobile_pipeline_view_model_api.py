from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_pipeline_view_model_exposes_patch_as_preview_not_direct_apply():
    client = TestClient(create_app())

    response = client.get("/api/v1/mobile/view-model/pipeline/task_test")

    assert response.status_code == 200
    data = response.json()
    patch_card = next(card for card in data["cards"] if card["card_type"] == "patch_preview")
    assert patch_card["status"] == "blocked"
    assert patch_card["metadata"]["direct_apply_visible"] is False
