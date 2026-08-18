from aipinho.services.validation.limitation_honesty_validator import LimitationHonestyValidator
from validation_fixtures import valid_report


def test_limitation_honesty_requires_limitations_for_partial():
    report = valid_report("partial")
    report["limitations"] = []
    findings = LimitationHonestyValidator().validate(report)
    assert any(item.code == "missing_limitations_when_partial" for item in findings)


def test_limitation_honesty_warns_overconfident_partial():
    report = valid_report("partial")
    report["executive_summary"] = "Com certeza tudo esta perfeito."
    findings = LimitationHonestyValidator().validate(report)
    assert any(item.code == "unsupported_claim" for item in findings)
