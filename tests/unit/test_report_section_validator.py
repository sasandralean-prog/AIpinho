from aipinho.services.validation.report_section_validator import ReportSectionValidator
from validation_fixtures import valid_report


def test_report_section_validator_accepts_json_fields():
    assert ReportSectionValidator().validate(valid_report()) == []


def test_report_section_validator_rejects_missing_executive_summary():
    report = valid_report()
    report["executive_summary"] = ""
    findings = ReportSectionValidator().validate(report)
    assert any(item.code == "missing_required_section" for item in findings)
