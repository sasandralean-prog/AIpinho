from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_task_draft_api_readonly_get_refresh_delete():
    created = client.post("/api/v1/task-drafts", json={"prompt": r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada"})
    assert created.status_code == 200
    draft = created.json()["draft"]
    assert draft["contract_type"] == "readonly_analysis"
    assert draft["safe_to_execute"] is False
    draft_id = draft["draft_id"]

    fetched = client.get(f"/api/v1/task-drafts/{draft_id}")
    assert fetched.status_code == 200
    assert fetched.json()["draft"]["draft_id"] == draft_id

    refreshed = client.post(f"/api/v1/task-drafts/{draft_id}/refresh-policy")
    assert refreshed.status_code == 200

    events = client.get(f"/api/v1/task-drafts/{draft_id}/events")
    assert events.status_code == 200
    assert events.json()["events"]

    deleted = client.delete(f"/api/v1/task-drafts/{draft_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_task_draft_api_forbidden_root_blocked():
    response = client.post("/api/v1/task-drafts", json={"prompt": r"Corrija C:\PinhoabacaxiAI"})
    assert response.status_code == 200
    draft = response.json()["draft"]
    assert draft["status"] == "blocked"
    assert draft["workspace"]["status"] == "protected"


def test_task_draft_api_conversation_not_applicable():
    response = client.post("/api/v1/task-drafts", json={"prompt": "Bom dia"})
    assert response.status_code == 200
    assert response.json()["status"] == "not_applicable"