from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_session_api_create_get_events_delete():
    created = client.post("/api/v1/sessions", json={"surface": "api"})
    assert created.status_code == 200
    session = created.json()["session"]
    session_id = session["session_id"]
    assert session["recent_messages"] == []

    fetched = client.get(f"/api/v1/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["session"]["session_id"] == session_id

    events = client.get(f"/api/v1/sessions/{session_id}/events")
    assert events.status_code == 200
    assert events.json()["events"]

    deleted = client.delete(f"/api/v1/sessions/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_session_api_does_not_expose_raw_secret_after_chat():
    created = client.post("/api/v1/sessions", json={"surface": "api"}).json()["session"]
    session_id = created["session_id"]
    response = client.post("/api/v1/chat", json={"session_id": session_id, "message": "token=abc123"})
    assert response.status_code == 200
    session = client.get(f"/api/v1/sessions/{session_id}").json()["session"]
    assert "token=abc123" not in str(session)