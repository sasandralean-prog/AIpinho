from aipinho.services.validation.report_quality_gate_service import ReportQualityGateService
from validation_fixtures import report_missing_evidence, valid_report


def test_report_quality_gate_accepts_valid_report():
    result = ReportQualityGateService().validate_report(valid_report())
    assert result.status in {"passed", "passed_with_warnings"}


def test_report_quality_gate_rejects_empty_report():
    result = ReportQualityGateService().validate_report({})
    assert result.status == "rejected"
    assert "empty_output" in result.blocking_findings


def test_report_quality_gate_rejects_missing_evidence():
    result = ReportQualityGateService().validate_report(report_missing_evidence())
    assert result.status == "rejected"
