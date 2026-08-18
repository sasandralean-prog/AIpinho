from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    return TestClient(app)


def test_agent_kernel_profiles_and_session_flow(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    agents = client.get("/api/v1/agents")
    assert agents.status_code == 200
    agent_ids = {agent["agent_id"] for agent in agents.json()["agents"]}
    assert {"aipinho", "lucio", "codex", "gemini"}.issubset(agent_ids)

    created = client.post("/api/v1/agents/aipinho/sessions", json={"title": "Kernel Chat"})
    assert created.status_code == 200
    session_id = created.json()["session"]["session_id"]

    renamed = client.patch(f"/api/v1/agents/aipinho/sessions/{session_id}", json={"title": "Kernel Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["session"]["title"] == "Kernel Renamed"

    listed = client.get("/api/v1/agents/aipinho/sessions", params={"include_compat": False})
    assert listed.status_code == 200
    assert [session["session_id"] for session in listed.json()["sessions"]] == [session_id]

    deleted = client.delete(f"/api/v1/agents/aipinho/sessions/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json()["session"]["deleted"] is True


def test_agent_kernel_messages_hide_raw_and_do_not_cross_agents(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    aipinho = client.post("/api/v1/agents/aipinho/sessions", json={"title": "AIpinho"}).json()["session"]["session_id"]
    codex = client.post("/api/v1/agents/codex/sessions", json={"title": "Codex"}).json()["session"]["session_id"]

    created = client.post(
        f"/api/v1/agents/aipinho/sessions/{aipinho}/messages",
        json={"role": "user", "content_sanitized": "Ola", "raw_ref": "raw_agent_test"},
    )
    assert created.status_code == 200
    assert "raw_ref" not in created.json()["message"]
    assert created.json()["message"]["raw_available"] is True

    codex_messages = client.get(f"/api/v1/agents/codex/sessions/{codex}/messages")
    assert codex_messages.status_code == 200
    assert codex_messages.json()["messages"] == []


def test_agent_kernel_compatibility_chat_status_still_works(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.get("/api/v1/chat/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
