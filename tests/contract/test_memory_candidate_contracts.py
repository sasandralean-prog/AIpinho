from aipinho.schemas.memory.memory_candidate import (
    MemoryCandidateEvidence,
    MemoryCandidateRequest,
    MemoryCandidateRisk,
    MemoryCandidateScope,
    MemoryCandidateSource,
    MemoryExtractionResult,
)


def test_memory_candidate_request_contract():
    request = MemoryCandidateRequest(
        text="Reports require quality gate.",
        kind="policy_decision",
        source=MemoryCandidateSource(source_type="manual_payload", source_id="s1"),
        scope=MemoryCandidateScope(scope_type="policy"),
        evidence=[MemoryCandidateEvidence(evidence_id="e1", evidence_type="policy_decision", source_ref="s1", summary="Evidence")],
    )
    assert request.text
    assert request.source.source_type == "manual_payload"


def test_memory_candidate_risk_contract():
    risk = MemoryCandidateRisk(level="high", reasons=["conflict"], approval_future_required=True)
    assert risk.level == "high"


def test_memory_extraction_result_contract():
    result = MemoryExtractionResult(status="ok", source=MemoryCandidateSource(source_type="manual_payload"))
    assert result.candidate_only is True
    assert result.approved_memory_enabled is False
    assert result.vectorstore_enabled is False
