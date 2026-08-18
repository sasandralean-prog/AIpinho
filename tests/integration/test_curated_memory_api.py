from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.schemas.memory.memory_candidate import MemoryCandidateEvidence, MemoryCandidateRequest, MemoryCandidateScope, MemoryCandidateSource


def test_curated_memory_api_status_and_candidate_approval_flow():
    client = TestClient(create_app())
    status = client.get("/api/v1/memory/status")
    assert status.status_code == 200
    assert status.json()["curated_memory"]["enabled"] is True

    candidate_payload = MemoryCandidateRequest(
        text="Sprint API test memory requires explicit approval.",
        kind="policy_decision",
        source=MemoryCandidateSource(source_type="manual_payload", source_id="api-test", source_ref="manual:api-test", trusted=True),
        scope=MemoryCandidateScope(scope_type="policy", reason="integration_test"),
        evidence=[MemoryCandidateEvidence(evidence_id="ev-api", evidence_type="policy_decision", source_ref="manual:api-test", summary="Evidence")],
    ).model_dump()
    candidate_response = client.post("/api/v1/memory/candidates", json=candidate_payload)
    assert candidate_response.status_code == 200
    candidate_id = candidate_response.json()["candidate"]["candidate_id"]

    approval_response = client.post(f"/api/v1/memory/approvals/from-candidate/{candidate_id}", json={"candidate_id": candidate_id, "reason": "integration"})
    assert approval_response.status_code == 200
    assert approval_response.json()["approved_memory_enabled"] is True
    assert client.get("/api/v1/memory/curated/status").status_code == 200
