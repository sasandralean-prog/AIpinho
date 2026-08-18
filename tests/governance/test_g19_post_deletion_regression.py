from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_g19_public_chat_and_continue_routes_survive_legacy_cleanup() -> None:
    client = TestClient(create_app())
    chat = client.post(
        "/api/v1/chat",
        json={"message": "Somente planejamento textual. Nao escrever arquivos. product_planning_readonly", "context": {"surface": "api"}},
    )
    assert chat.status_code == 200
    assert chat.json()["governance_lifecycle"]["intent"]["intent_type"] == "product_planning_readonly"

    models = client.get("/v1/models")
    assert models.status_code == 200
    assert models.json()["object"] == "list"
