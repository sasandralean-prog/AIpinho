from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import PolicyDecision
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.multi_agent_policy_audit_store import MultiAgentPolicyAuditStore


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy_kernel"))
    monkeypatch.setenv("AIPINHO_SELF_HEALING_ROOT", str(tmp_path / "self_healing"))
    return TestClient(app)


def test_multi_agent_dashboard_and_debugger_events_are_sanitized(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    service = AgentSessionKernelService()
    session = service.create_session("aipinho", AgentSessionCreateRequest(title="Observability"))
    run = service.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="analysis", status="running"))
    event = service.add_event(
        run.run_id,
        AgentEventCreateRequest(
            event_type="analysis_started",
            status="running",
            severity="info",
            human_message="Analise iniciada sem raw.",
            payload_sanitized={"token": "Bearer SHOULD_NOT_LEAK"},
        ),
    )

    dashboard = client.get("/api/v1/dashboard/multi-agent")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["raw_default_visible"] is False
    assert payload["active_runs"][0]["run_id"] == run.run_id
    assert any(card["card_id"] == "multi_agent_active_runs" for card in payload["cards"])

    events = client.get("/api/v1/debugger/events", params={"agent_id": "aipinho"})
    assert events.status_code == 200
    event_payload = events.json()
    assert event_payload["raw_default_visible"] is False
    assert any(item["event_id"] == event.event_id for item in event_payload["events"])
    assert "SHOULD_NOT_LEAK" not in str(event_payload)
    assert "[REDACTED_SECRET]" in str(event_payload)


def test_debugger_trace_and_entity_for_agent_run(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    service = AgentSessionKernelService()
    session = service.create_session("codex", AgentSessionCreateRequest(title="Trace"))
    run = service.create_run("codex", session.session_id, AgentRunCreateRequest(operation_type="tool_test", status="running"))
    service.add_event(
        run.run_id,
        AgentEventCreateRequest(
            event_type="tool_test_started",
            status="running",
            severity="info",
            human_message="Tool test em execucao.",
            tool_invocation_id="tool_invocation_test",
        ),
    )

    trace = client.get(f"/api/v1/debugger/traces/{run.run_id}")
    assert trace.status_code == 200
    assert trace.json()["trace_graph"]["run_id"] == run.run_id
    assert any(node["node_type"] == "run" for node in trace.json()["trace_graph"]["nodes"])

    entity = client.get(f"/api/v1/debugger/entities/run/{run.run_id}")
    assert entity.status_code == 200
    assert entity.json()["entity"]["run_id"] == run.run_id


def test_state_consistency_endpoint_returns_structured_report(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    report = client.get("/api/v1/dashboard/state-consistency")
    assert report.status_code == 200
    assert "issues" in report.json()
    assert "counts" in report.json()


def test_cancelled_run_does_not_leave_policy_approval_on_dashboard(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    service = AgentSessionKernelService()
    session = service.create_session("aipinho", AgentSessionCreateRequest(title="Approval hygiene"))
    run = service.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(operation_type="create_file", status="cancelled"),
    )
    MultiAgentPolicyAuditStore().save_policy_decision(
        PolicyDecision(
            agent_id="aipinho",
            session_id=session.session_id,
            run_id=run.run_id,
            operation_type="create_file",
            capability="workspace_write",
            decision="require_approval",
            reason_code="approval_required",
            human_reason="A escrita exige aprovacao.",
            technical_reason_sanitized="approval_required",
            approval_required=True,
        )
    )

    dashboard = client.get("/api/v1/dashboard/multi-agent")

    assert dashboard.status_code == 200
    assert dashboard.json()["pending_approvals"] == []
