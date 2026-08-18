
from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.agents.contracts import AgentRunCreateRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService


def test_agent_delegation_api_creates_lineage_events_result_and_cancel(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    client = TestClient(app)
    session = client.post("/api/v1/agents/lucio/sessions", json={"title": "Lucio API"}).json()["session"]
    parent = AgentSessionKernelService().create_run(
        "lucio",
        session["session_id"],
        AgentRunCreateRequest(
            operation_type="coordination",
            status="running",
            metadata_sanitized={"execution_mode": "governed_autorun"},
        ),
    )

    created = client.post(
        f"/api/v1/agents/lucio/runs/{parent.run_id}/delegate",
        json={
            "target_agent_id": "codex",
            "user_goal": "Review a design safely",
            "requested_operation": "technical_analysis",
            "capabilities_requested": ["technical_analysis", "read_workspace"],
            "risk_level": "low",
        },
    )
    assert created.status_code == 200
    body = created.json()
    delegation = body["delegation"]
    assert body["status"] == "running"
    assert delegation["parent_run_id"] == parent.run_id
    assert delegation["child_run_id"]

    children = client.get(f"/api/v1/agents/runs/{parent.run_id}/children")
    assert children.status_code == 200
    assert children.json()["children"][0]["delegation_id"] == delegation["delegation_id"]

    parent_link = client.get(f"/api/v1/agents/runs/{delegation['child_run_id']}/parent")
    assert parent_link.status_code == 200
    assert parent_link.json()["parent"]["parent_run_id"] == parent.run_id

    events = client.get(f"/api/v1/agents/delegations/{delegation['delegation_id']}/events", params={"include_child_events": True})
    assert events.status_code == 200
    event_types = {event["event_type"] for event in events.json()["events"]}
    assert "delegation_created" in event_types
    assert "delegation_child_run_started" in event_types

    result = client.get(f"/api/v1/agents/delegations/{delegation['delegation_id']}/result")
    assert result.status_code == 200
    assert result.json()["result"]["status"] == "running"

    cancelled = client.post(f"/api/v1/agents/delegations/{delegation['delegation_id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
