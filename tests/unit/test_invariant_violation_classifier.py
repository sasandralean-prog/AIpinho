from aipinho.schemas.maintenance.contracts import InvariantEvidence, InvariantViolation
from aipinho.services.maintenance.invariant_violation_classifier import InvariantViolationClassifier

def test_classifies_highest_severity():
    values = [InvariantViolation(invariant_id="a", severity="medium", description="a", evidence=InvariantEvidence(invariant_id="a"), recommended_action="inspect"), InvariantViolation(invariant_id="b", severity="critical", description="b", evidence=InvariantEvidence(invariant_id="b"), recommended_action="block")]
    assert InvariantViolationClassifier().highest(values) == "critical"
