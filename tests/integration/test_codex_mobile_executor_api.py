from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app


def test_codex_mobile_run_events_and_view_model_api(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_AGENT_ENABLED", "false")
    monkeypatch.setenv("AIPINHO_CODEX_AGENT_ROOT", str(tmp_path / "codex_agent"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "agent_memory"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy_kernel"))
    monkeypatch.setenv("AIPINHO_EVENT_STORE_ROOT", str(tmp_path / "events" / "store"))
    monkeypatch.setenv("AIPINHO_EVENT_RAW_ROOT", str(tmp_path / "events" / "raw"))
    monkeypatch.setenv("AIPINHO_EVENT_AUDIT_ROOT", str(tmp_path / "events" / "audit"))
    client = TestClient(app)

    created = client.post("/api/v1/codex-agent/sessions", json={"title": "Mobile Codex"})
    assert created.status_code == 200
    session_id = created.json()["session"]["session_id"]

    sent = client.post(
        f"/api/v1/codex-agent/sessions/{session_id}/send",
        json={
            "session_id": session_id,
            "prompt": "Explique em uma frase.",
            "requested_capabilities": ["read_workspace"],
            "autorun_enabled": True,
            "autoreview_enabled": True,
            "autoapproval_enabled": True,
        },
    )
    assert sent.status_code == 200
    response = sent.json()["response"]
    run_id = response["run_id"]
    assert run_id

    events = client.get(f"/api/v1/codex-agent/runs/{run_id}/events")
    assert events.status_code == 200
    payload = events.json()
    assert payload["events"]
    assert any(event["event_type"] == "codex_auto_approval_granted" for event in payload["events"])

    after = payload["events"][0]["event_id"]
    incremental = client.get(f"/api/v1/codex-agent/runs/{run_id}/events", params={"after_event_id": after})
    assert incremental.status_code == 200
    assert all(event["event_id"] != after for event in incremental.json()["events"])

    view_model = client.get("/api/v1/mobile/codex/view-model", params={"session_id": session_id, "after_event_id": after})
    assert view_model.status_code == 200
    body = view_model.json()
    assert body["raw_default_visible"] is False
    assert body["token_in_url"] is False
    assert body["active_run"]["run_id"] == run_id

    agent_view_model = client.get(
        f"/api/v1/codex-agent/sessions/{session_id}/view-model",
        params={"after_event_id": after},
    )
    assert agent_view_model.status_code == 200
    agent_body = agent_view_model.json()
    assert agent_body["raw_default_visible"] is False
    assert agent_body["active_run"]["run_id"] == run_id
