from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def valid_payload(text="Patch apply requires quality gate passed."):
    return {
        "text": text,
        "kind": "policy_decision",
        "source": {"source_type": "manual_payload", "source_id": "api_src", "source_ref": "manual:api_src", "trusted": True},
        "scope": {"scope_type": "policy", "reason": "api_test"},
        "evidence": [{"evidence_id": "api_ev", "evidence_type": "policy_decision", "source_ref": "manual:api_src", "summary": "API evidence"}],
    }


def test_memory_status_endpoint():
    response = client.get("/api/v1/memory/status")
    assert response.status_code == 200
    data = response.json()
    assert data["memory_candidate_enabled"] is True
    assert data["approved_memory_enabled"] is True
    assert data["curated_memory"]["approval_required"] is True
    assert data["curated_memory"]["auto_prompt_memory_enabled"] is False
    assert data["vectorstore_enabled"] is False


def test_create_list_evidence_trace_reject_candidate():
    created = client.post("/api/v1/memory/candidates", json=valid_payload()).json()
    candidate_id = created["candidate"]["candidate_id"]
    assert created["candidate"]["status"] in {"candidate", "needs_review", "duplicate"}
    assert client.get(f"/api/v1/memory/candidates/{candidate_id}").status_code == 200
    assert client.get(f"/api/v1/memory/candidates/{candidate_id}/evidence").status_code == 200
    assert client.get(f"/api/v1/memory/candidates/{candidate_id}/trace").status_code == 200
    assert client.get(f"/api/v1/memory/candidates/{candidate_id}/events").status_code == 200
    assert client.get("/api/v1/memory/candidates").status_code == 200
    rejected = client.post(f"/api/v1/memory/candidates/{candidate_id}/reject", json={"reason": "test"}).json()
    assert rejected["status"] == "rejected"


def test_extract_endpoint_and_approve_blocked():
    extracted = client.post("/api/v1/memory/candidates/extract", json={"source_type": "manual_payload", "payload": {"text": "Runtime policy must stay candidate only.", "kind": "policy_decision", "scope_type": "policy"}}).json()
    assert extracted["approved_memory_enabled"] is False
    blocked = client.post("/api/v1/memory/approve", json={"candidate_id": "x"}).json()
    assert blocked["status"] == "blocked"
    assert blocked["approved"] is False


def test_missing_evidence_api_blocks():
    payload = valid_payload()
    payload["evidence"] = []
    response = client.post("/api/v1/memory/candidates", json=payload)
    assert response.status_code == 200
    assert response.json()["candidate"]["status"] == "blocked"
