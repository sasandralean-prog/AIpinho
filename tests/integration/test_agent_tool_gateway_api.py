from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.agents.contracts import AgentRunCreateRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService


def test_tool_gateway_api_lists_tools():
    client = TestClient(app)
    response = client.get("/api/v1/agent-tool-gateway/tools")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "read_file" in {tool["tool_name"] for tool in payload["tools"]}


def test_tool_gateway_api_invokes_artifact_and_requires_download_token(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    client = TestClient(app)
    session = client.post("/api/v1/agents/aipinho/sessions", json={"title": "Tool API"}).json()["session"]
    service = AgentSessionKernelService()
    run = service.create_run("aipinho", session["session_id"], AgentRunCreateRequest(operation_type="artifact", status="running"))

    response = client.post(
        f"/api/v1/agents/aipinho/runs/{run.run_id}/tools/create_artifact/invoke",
        json={"input": {"filename": "result.txt", "content": "ok"}},
    )
    assert response.status_code == 200
    payload = response.json()
    artifact = payload["artifacts"][0]
    assert artifact["download_endpoint"] == f"/api/v1/agents/artifacts/{artifact['artifact_id']}/download"

    assert client.get(artifact["download_endpoint"]).status_code == 401
    downloaded = client.get(artifact["download_endpoint"], headers={"Authorization": "Bearer test-token"})
    assert downloaded.status_code == 200
    assert downloaded.text == "ok"
    timeline = client.get(f"/api/v1/agents/aipinho/sessions/{session['session_id']}/timeline?mode=details").json()
    assert "artifact_created" in {event["event_type"] for event in timeline["events"]}
