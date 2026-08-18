from aipinho.services.validation.evidence_compliance_validator import EvidenceComplianceValidator
from validation_fixtures import report_missing_evidence, valid_report


def test_evidence_compliance_accepts_valid_evidence():
    assert EvidenceComplianceValidator().validate({"report": valid_report()}) == []


def test_evidence_compliance_rejects_missing_evidence():
    findings = EvidenceComplianceValidator().validate({"report": report_missing_evidence()})
    assert any(item.code == "missing_evidence" for item in findings)


def test_evidence_compliance_rejects_invalid_evidence_id():
    report = valid_report()
    report["findings"][0]["evidence"][0]["evidence_id"] = "missing"
    findings = EvidenceComplianceValidator().validate({"report": report})
    assert any(item.code == "invalid_evidence" for item in findings)
