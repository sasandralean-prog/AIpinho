from aipinho.schemas.maintenance.contracts import DiagnosisEvidence
from aipinho.services.maintenance.confidence_estimator import ConfidenceEstimator

def test_direct_evidence_and_violation_yield_high_confidence():
    evidence = DiagnosisEvidence(source_type="event", source_id="event_unit", summary="Observed.", event_ref="event_unit", confidence=.95)
    result = ConfidenceEstimator().estimate([evidence], [object()])
    assert result.level == "high"
