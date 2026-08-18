from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    return TestClient(app)


def test_agent_timeline_api_incremental_and_mobile_view_model(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    session = client.post("/api/v1/agents/aipinho/sessions", json={"title": "Timeline"}).json()["session"]
    run = client.post(
        "/api/v1/agents/aipinho/sessions/{}/messages".format(session["session_id"]),
        json={"role": "user", "content_sanitized": "Hello"},
    )
    assert run.status_code == 200

    # Runs are created through service-level contract for now; use API-visible event path after creating a run indirectly is out of Sprint 2 scope.
    from aipinho.schemas.agents.contracts import AgentRunCreateRequest
    from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService

    service = AgentSessionKernelService()
    created_run = service.create_run("aipinho", session["session_id"], AgentRunCreateRequest(operation_type="analysis", status="running"))
    event = client.post(
        f"/api/v1/agents/runs/{created_run.run_id}/events",
        json={"event_type": "agent_run_started", "human_message": "Started"},
    )
    assert event.status_code == 200
    event_id = event.json()["event"]["event_id"]

    timeline = client.get(f"/api/v1/agents/aipinho/sessions/{session['session_id']}/timeline")
    assert timeline.status_code == 200
    payload = timeline.json()
    assert payload["polling"]["enabled"] is True
    assert payload["next_poll_seconds"] == 5
    assert payload["cards"][0]["event_id"] == event_id

    incremental = client.get(f"/api/v1/agents/aipinho/sessions/{session['session_id']}/timeline", params={"after_event_id": event_id})
    assert incremental.status_code == 200
    assert incremental.json()["events"] == []

    mobile = client.get("/api/v1/mobile/agents/aipinho/view-model", params={"session_id": session["session_id"]})
    assert mobile.status_code == 200
    assert mobile.json()["raw_default_visible"] is False
    assert mobile.json()["polling"]["recommended_interval_seconds"] == 5


def test_run_events_api_hides_raw_by_default_and_details_show_metadata(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    session = client.post("/api/v1/agents/codex/sessions", json={"title": "Codex"}).json()["session"]

    from aipinho.schemas.agents.contracts import AgentRunCreateRequest
    from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService

    service = AgentSessionKernelService()
    run = service.create_run("codex", session["session_id"], AgentRunCreateRequest(operation_type="shell", status="running"))
    response = client.post(
        f"/api/v1/agents/runs/{run.run_id}/events",
        json={
            "event_type": "shell_stdout",
            "human_message": "Bearer SECRET_VALUE_12345",
            "payload_sanitized": {"Authorization": "Bearer SECRET_VALUE_12345"},
            "raw_ref": "raw_hidden",
        },
    )
    assert response.status_code == 200

    normal = client.get(f"/api/v1/agents/runs/{run.run_id}/events")
    card = normal.json()["cards"][0]
    assert "[REDACTED_SECRET]" in card["body"]
    assert "raw_ref" not in card
    assert card["raw_available"] is True
    assert card["details"] == {}

    details = client.get(f"/api/v1/agents/runs/{run.run_id}/events", params={"mode": "details"})
    assert details.status_code == 200
    detail_card = next(card for card in details.json()["cards"] if card["event_type"] == "shell_stdout")
    assert detail_card["details"]["event_type"] == "shell_stdout"


def test_existing_chat_status_still_works_with_agent_mobile_router(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.get("/api/v1/chat/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
