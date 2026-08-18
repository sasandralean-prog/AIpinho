from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def payload(text, *, kind="policy_decision", scope_type="policy", evidence=True, status=None):
    data = {
        "text": text,
        "kind": kind,
        "source": {"source_type": "manual_payload", "source_id": text[:12], "source_ref": "e2e", "trusted": True},
        "scope": {"scope_type": scope_type, "reason": "e2e"},
        "evidence": [{"evidence_id": "e2e_ev", "evidence_type": "policy_decision", "source_ref": "e2e", "summary": "Evidence"}] if evidence else [],
    }
    if status:
        data["status"] = status
    return data


def test_candidate_layer_required_cases():
    status = client.get("/api/v1/memory/status").json()
    assert status["memory_candidate_enabled"] is True
    assert status["approved_memory_enabled"] is True
    assert status["curated_memory"]["candidate_required"] is True
    assert status["curated_memory"]["auto_prompt_memory_enabled"] is False
    assert status["vectorstore_enabled"] is False
    assert status["embeddings_enabled"] is False
    assert status["rag_enabled"] is False

    valid = client.post("/api/v1/memory/candidates", json=payload("Reports generated must pass quality gate.")).json()["candidate"]
    assert valid["status"] in {"candidate", "needs_review", "duplicate"}

    no_scope = payload("Technical memory without scope.", scope_type="")
    assert client.post("/api/v1/memory/candidates", json=no_scope).json()["candidate"]["status"] == "blocked"

    no_evidence = payload("Technical memory without evidence.", evidence=False)
    assert client.post("/api/v1/memory/candidates", json=no_evidence).json()["candidate"]["status"] == "blocked"

    secret = payload("api_key=abcdef12345 must be blocked.")
    secret_result = client.post("/api/v1/memory/candidates", json=secret).json()["candidate"]
    assert secret_result["status"] == "blocked"
    assert "abcdef12345" not in secret_result["text"]

    approved = payload("Approved status is forbidden.", status="approved")
    assert client.post("/api/v1/memory/candidates", json=approved).json()["candidate"]["status"] == "blocked"

    duplicate_1 = client.post("/api/v1/memory/candidates", json=payload("Patch apply requires explicit approval and post validation.")).json()["candidate"]
    duplicate_2 = client.post("/api/v1/memory/candidates", json=payload("Patch apply requires explicit approval and post validation.")).json()["candidate"]
    assert duplicate_1["candidate_id"] != duplicate_2["candidate_id"]
    assert duplicate_2["status"] == "duplicate"

    user_instruction = client.post("/api/v1/memory/candidates", json=payload("User wants this as a future memory candidate.", kind="user_instruction", scope_type="user_instruction", evidence=False)).json()["candidate"]
    assert user_instruction["status"] in {"candidate", "needs_review", "duplicate"}

    approve = client.post("/api/v1/memory/approve", json={"candidate_id": valid["candidate_id"]}).json()
    assert approve["approved"] is False
