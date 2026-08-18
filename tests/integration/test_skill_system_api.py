from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app


def test_skill_api_lists_health_and_mobile_view(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_SKILL_REGISTRY_ROOT", str(tmp_path / "skill_registry"))
    client = TestClient(app)

    skills = client.get("/api/v1/skills")
    health = client.get("/api/v1/skills/health")
    mobile = client.get("/api/v1/mobile/view-model/skills")

    assert skills.status_code == 200
    assert health.status_code == 200
    assert mobile.status_code == 200
    assert skills.json()["skills"]
    assert mobile.json()["state"]["raw_default_visible"] is False


def test_skill_api_executes_report_skill_with_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_SKILL_REGISTRY_ROOT", str(tmp_path / "skill_registry"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    client = TestClient(app)
    session = client.post("/api/v1/agents/aipinho/sessions", json={"title": "Skill API"}).json()["session"]

    response = client.post(
        "/api/v1/skills/internal.safe_markdown_report_generator/execute",
        json={
            "skill_id": "internal.safe_markdown_report_generator",
            "requesting_agent_id": "aipinho",
            "session_id": session["session_id"],
            "requested_capabilities": ["report_generate", "artifact_create"],
            "inputs": {"title": "API skill report", "summary": "ok"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["output_artifact_refs"]
    assert payload["policy_decision_ids"]
    assert payload["speaker_truth_status"] == "raw_hidden_by_default"


def test_skill_api_blocks_missing_capability(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_SKILL_REGISTRY_ROOT", str(tmp_path / "skill_registry"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    client = TestClient(app)
    session = client.post("/api/v1/agents/aipinho/sessions", json={"title": "Skill API"}).json()["session"]

    response = client.post(
        "/api/v1/skills/internal.safe_markdown_report_generator/execute",
        json={
            "skill_id": "internal.safe_markdown_report_generator",
            "requesting_agent_id": "aipinho",
            "session_id": session["session_id"],
            "requested_capabilities": ["report_generate"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "missing_capability:artifact_create" in payload["blocked_reasons"]
