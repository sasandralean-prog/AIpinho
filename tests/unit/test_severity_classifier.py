from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.services.reports.severity_classifier import SeverityClassifier


def test_severity_classifier_downgrades_missing_inference_and_weak_critical():
    classifier = SeverityClassifier()
    one = [EvidenceCitation(evidence_id="e1", source_type="file", path="a.py", confidence=0.7)]
    two = [*one, EvidenceCitation(evidence_id="e2", source_type="file", path="b.py", confidence=0.7)]

    assert classifier.classify("critical", [], tags=[])[0] == "low"
    assert classifier.classify("high", one)[0] == "medium"
    assert classifier.classify("medium", one, inference_only=True)[0] == "low"
    assert classifier.classify("critical", two, tags=["security_violation"])[0] == "critical"
