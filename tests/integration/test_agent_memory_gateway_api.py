from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app


def test_agent_memory_gateway_api_write_search_candidate_and_context(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "memory_gateway"))
    client = TestClient(app)

    status = client.get("/api/v1/agents/memory/status")
    assert status.status_code == 200
    assert status.json()["mode"] == "multi_agent_memory_gateway"

    namespaces = client.get("/api/v1/agents/memory/namespaces")
    assert namespaces.status_code == 200
    assert "memory:aipinho" in {row["namespace"] for row in namespaces.json()["namespaces"]}

    private_write = client.post(
        "/api/v1/agents/memory/memory:aipinho/records",
        json={
            "agent_id": "aipinho",
            "namespace": "memory:aipinho",
            "title": "Conversation routing",
            "content_sanitized": "Simple chat messages stay in conversation mode unless side effects are requested.",
            "memory_type": "prompt_routing_lesson",
            "source_ref": "report:api",
            "evidence_refs": ["report:api"],
            "confidence": "high",
        },
    )
    assert private_write.status_code == 200
    assert private_write.json()["status"] == "written"

    search = client.post(
        "/api/v1/agents/memory/search",
        json={"agent_id": "aipinho", "query": "simple side effects"},
    )
    assert search.status_code == 200
    assert search.json()["records"]

    shared_candidate = client.post(
        "/api/v1/agents/memory/candidates",
        json={
            "proposed_by_agent_id": "gemini",
            "namespace": "memory:shared",
            "scope": "shared",
            "title": "Shared evidence refs",
            "content_sanitized": "Shared memory should cite sanitized evidence refs.",
            "memory_type": "workflow_lesson",
            "source_ref": "report:api",
            "evidence_refs": ["report:api"],
            "confidence": "high",
            "reason_to_remember": "Reusable governance lesson.",
        },
    )
    assert shared_candidate.status_code == 200
    candidate_id = shared_candidate.json()["candidate"]["candidate_id"]

    accepted = client.post(
        f"/api/v1/agents/memory/candidates/{candidate_id}/accept",
        json={"agent_id": "aipinho", "reviewed_by": "aipinho"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "written"
    assert accepted.json()["memory"]["validation_status"] == "validated"

    context = client.get("/api/v1/agents/memory/agents/aipinho/context")
    assert context.status_code == 200
    assert context.json()["memory_refs_used"]
