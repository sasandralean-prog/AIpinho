from aipinho.schemas.maintenance.contracts import DiagnosisConfidence, DiagnosisEvidence, InvariantEvidence, InvariantViolation
from aipinho.services.maintenance.root_cause_analyzer import RootCauseAnalyzer

def test_root_cause_is_candidate_with_evidence():
    evidence = DiagnosisEvidence(source_type="event_summary", source_id="event_unit", summary="Observed.", event_ref="event_unit")
    violation = InvariantViolation(invariant_id="unit", severity="high", description="Unit violation.", evidence=InvariantEvidence(invariant_id="unit"), recommended_action="inspect")
    values = RootCauseAnalyzer().analyze([violation], [evidence], DiagnosisConfidence(level="high", score=.9))
    assert values[0].confidence.level == "high"
    assert evidence.evidence_id in values[0].evidence_refs
