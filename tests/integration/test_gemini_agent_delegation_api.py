from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("GEMINI_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("GEMINI_AGENT_USE_DELEGATION", "true")
    monkeypatch.setenv("GEMINI_AGENT_PREFER_AIPINHO_EXECUTOR", "true")
    monkeypatch.setenv("AIPINHO_GEMINI_EXECUTOR_ROOT", str(tmp_path / "gemini_store"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "memory"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy"))
    monkeypatch.setenv("AIPINHO_EVENT_STORE_ROOT", str(tmp_path / "events"))
    monkeypatch.setenv("AIPINHO_EVENT_RAW_ROOT", str(tmp_path / "raw"))
    monkeypatch.setenv("AIPINHO_EVENT_AUDIT_ROOT", str(tmp_path / "audit"))
    return TestClient(app)


def test_gemini_readonly_request_exposes_delegation_events_and_mobile_view_model(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    created = client.post("/api/v1/gemini-executor/sessions", json={"title": "Cloud review"})
    assert created.status_code == 200
    session_id = created.json()["session"]["session_id"]

    sent = client.post(
        f"/api/v1/gemini-executor/sessions/{session_id}/send",
        json={
            "session_id": session_id,
            "prompt": "Analise o workspace autorizado sem alterar arquivos.",
            "operation_type": "readonly_analysis",
            "workspace_id": "workspace_test",
            "requested_capabilities": ["read_workspace"],
        },
    )
    assert sent.status_code == 200
    response = sent.json()["response"]
    assert response["status"] == "delegation_running"
    assert response["delegation_id"]
    assert response["child_run_id"]
    assert response["run_id"]
    assert response["cloud_warning_visible"] is True

    events = client.get(f"/api/v1/gemini-executor/runs/{response['run_id']}/events")
    assert events.status_code == 200
    event_types = {event["event_type"] for event in events.json()["events"]}
    assert "delegation_created" in event_types
    assert "gemini_delegation_created" in event_types

    mobile = client.get(f"/api/v1/gemini-executor/sessions/{session_id}/view-model")
    assert mobile.status_code == 200
    payload = mobile.json()
    assert payload["raw_default_visible"] is False
    assert payload["token_in_url"] is False
    assert payload["active_run"]["run_id"] == response["run_id"]
    assert [message["role"] for message in payload["messages"]] == ["user", "assistant"]
