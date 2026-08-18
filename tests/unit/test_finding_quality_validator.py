from aipinho.services.validation.finding_quality_validator import FindingQualityValidator
from validation_fixtures import valid_finding


def test_finding_quality_validator_accepts_valid_finding():
    assert FindingQualityValidator().validate(valid_finding()) == []


def test_finding_quality_validator_rejects_missing_category():
    item = valid_finding()
    item["category"] = "unknown"
    findings = FindingQualityValidator().validate(item)
    assert any(item.code == "missing_category" for item in findings)


def test_finding_quality_validator_rejects_critical_weak_evidence():
    item = valid_finding(severity="critical")
    findings = FindingQualityValidator().validate(item)
    assert any(item.code == "weak_evidence" for item in findings)


def test_finding_quality_validator_warns_unsafe_recommendation():
    item = valid_finding()
    item["recommendation"] = "apply patch agora"
    findings = FindingQualityValidator().validate(item)
    assert any(item.code == "unsafe_recommendation" for item in findings)
