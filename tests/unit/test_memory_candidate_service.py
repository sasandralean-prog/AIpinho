from aipinho.schemas.memory.memory_candidate import MemoryCandidateEvidence, MemoryCandidateRequest, MemoryCandidateScope, MemoryCandidateSource
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore


def service(tmp_path):
    return MemoryCandidateService(store=MemoryCandidateStore(root=tmp_path))


def valid_request(text="Patch apply requires quality gate passed."):
    return MemoryCandidateRequest(
        text=text,
        kind="policy_decision",
        source=MemoryCandidateSource(source_type="manual_payload", source_id="src1", source_ref="manual:src1", trusted=True),
        scope=MemoryCandidateScope(scope_type="policy", reason="test"),
        evidence=[MemoryCandidateEvidence(evidence_id="ev1", evidence_type="policy_decision", source_ref="manual:src1", summary="Policy evidence")],
    )


def test_create_valid_candidate(tmp_path):
    result = service(tmp_path).create_candidate(valid_request())
    assert result.candidate is not None
    assert result.candidate.status in {"candidate", "needs_review"}
    assert result.approved_memory_enabled is False
    assert result.vectorstore_enabled is False


def test_missing_source_blocks(tmp_path):
    result = service(tmp_path).create_candidate(MemoryCandidateRequest(text="Technical rule.", kind="policy_decision", scope=MemoryCandidateScope(scope_type="policy")))
    assert result.candidate.status == "blocked"
    assert "source_missing" in result.candidate.blocked_reasons


def test_missing_evidence_blocks_technical_memory(tmp_path):
    req = valid_request()
    req.evidence = []
    result = service(tmp_path).create_candidate(req)
    assert result.candidate.status == "blocked"
    assert "evidence_missing_for_technical_memory" in result.candidate.blocked_reasons


def test_secret_is_blocked_and_redacted(tmp_path):
    req = valid_request("api_key=abcdef123456 should never be stored.")
    result = service(tmp_path).create_candidate(req)
    assert result.candidate.status == "blocked"
    assert "abcdef123456" not in result.candidate.text


def test_duplicate_candidate(tmp_path):
    svc = service(tmp_path)
    first = svc.create_candidate(valid_request()).candidate
    second = svc.create_candidate(valid_request()).candidate
    assert first is not None and second is not None
    assert second.status == "duplicate"
    assert second.dedupe.matched_candidate_id == first.candidate_id


def test_conflict_candidate_needs_review(tmp_path):
    svc = service(tmp_path)
    svc.create_candidate(valid_request("RAG enabled for policy checks."))
    result = svc.create_candidate(valid_request("RAG disabled for policy checks."))
    assert result.candidate.status in {"needs_review", "duplicate"}
    assert result.candidate.conflict.has_conflict or result.candidate.dedupe.status != "unique"


def test_approved_state_forbidden(tmp_path):
    req = valid_request()
    req.status = "approved"
    result = service(tmp_path).create_candidate(req)
    assert result.candidate.status == "blocked"
    assert "approved_state_forbidden_this_sprint" in result.candidate.blocked_reasons
