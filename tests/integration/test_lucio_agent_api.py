from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app


def test_lucio_disabled_endpoint_returns_agent_disabled_without_provider_call(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    monkeypatch.setenv("LUCIO_ENABLED", "false")
    monkeypatch.setenv("LUCIO_AGENT_ENABLED", "false")
    monkeypatch.setenv("LUCIO_PROVIDER", "disabled")
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    client = TestClient(app)

    health = client.get("/api/v1/lucio-agent/health")
    created = client.post("/api/v1/lucio-agent/sessions", json={"title": "Lucio"})

    assert health.status_code == 200
    assert health.json()["status"] == "disabled_by_config"
    assert health.json()["provider"] == "disabled"
    assert created.status_code == 200
    payload = created.json()
    assert payload["status"] == "blocked"
    assert payload["reason_code"] == "agent_disabled"
    assert payload["provider"] == "disabled"
    assert payload["local_execution_started"] is False
    assert payload["tool_invoked"] is False
    assert payload["delegation_started"] is False


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("LUCIO_ENABLED", "true")
    monkeypatch.setenv("LUCIO_AGENT_ENABLED", "true")
    monkeypatch.setenv("LUCIO_PROVIDER", "openai")
    monkeypatch.setenv("LUCIO_ALLOW_NEW_SESSIONS", "true")
    monkeypatch.setenv("LUCIO_AGENT_USE_DELEGATION", "true")
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "memory"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy"))
    monkeypatch.setenv("AIPINHO_EVENT_STORE_ROOT", str(tmp_path / "events"))
    monkeypatch.setenv("AIPINHO_EVENT_RAW_ROOT", str(tmp_path / "raw"))
    monkeypatch.setenv("AIPINHO_EVENT_AUDIT_ROOT", str(tmp_path / "audit"))
    return TestClient(app)


def test_lucio_api_delegates_technical_work_and_exposes_mobile_view_model(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    created = client.post("/api/v1/lucio-agent/sessions", json={"title": "Revisao"})
    assert created.status_code == 200
    session_id = created.json()["session"]["session_id"]

    preview = client.post(
        f"/api/v1/lucio-agent/sessions/{session_id}/route-preview",
        json={
            "session_id": session_id,
            "prompt": "Revise o codigo e rode os testes.",
            "operation_type": "code_review",
            "workspace_id": "workspace_test",
            "requested_capabilities": ["read_workspace", "code_review", "validation"],
        },
    )
    assert preview.status_code == 200
    assert preview.json()["route_decision"]["route"] == "delegate_codex"

    sent = client.post(
        f"/api/v1/lucio-agent/sessions/{session_id}/send",
        json={
            "session_id": session_id,
            "prompt": "Revise o codigo e rode os testes.",
            "operation_type": "code_review",
            "workspace_id": "workspace_test",
            "requested_capabilities": ["read_workspace", "code_review", "validation"],
        },
    )
    assert sent.status_code == 200
    response = sent.json()["response"]
    assert response["status"] == "delegation_running"
    assert response["delegation_id"]
    assert response["child_run_id"]

    events = client.get(f"/api/v1/lucio-agent/runs/{response['run_id']}/events")
    assert events.status_code == 200
    event_types = {event["event_type"] for event in events.json()["events"]}
    assert {"lucio_route_decided", "delegation_created", "delegation_child_run_started"} <= event_types

    mobile = client.get(f"/api/v1/lucio-agent/sessions/{session_id}/view-model")
    assert mobile.status_code == 200
    payload = mobile.json()
    assert payload["agent_id"] == "lucio"
    assert payload["raw_default_visible"] is False
    assert [message["role"] for message in payload["messages"]] == ["user", "assistant"]
