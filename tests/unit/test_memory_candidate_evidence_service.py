from aipinho.schemas.memory.memory_candidate import MemoryCandidateEvidence, MemoryCandidateSource
from aipinho.services.memory.memory_candidate_evidence_service import MemoryCandidateEvidenceService


def test_valid_evidence_medium_confidence():
    service = MemoryCandidateEvidenceService()
    evidence = [MemoryCandidateEvidence(evidence_id="e1", evidence_type="report_finding", source_ref="r1", summary="Evidence")]
    assert service.validate(evidence, kind="policy_decision") == []
    assert service.confidence(evidence=evidence, source=MemoryCandidateSource(source_type="project_report", source_id="r1", trusted=True), kind="policy_decision") == "medium"


def test_missing_evidence_id_fails():
    evidence = [MemoryCandidateEvidence(evidence_id="", evidence_type="report_finding", source_ref="r1", summary="Evidence")]
    assert "evidence_id_missing" in MemoryCandidateEvidenceService().validate(evidence, kind="policy_decision")
