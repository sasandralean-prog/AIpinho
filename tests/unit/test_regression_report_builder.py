from aipinho.schemas.regression.contracts import RegressionRunResult
from aipinho.services.regression.regression_report_builder import RegressionReportBuilder

def test_report_builder_creates_report():
    result = RegressionRunResult(case_id="case", status="passed")
    report = RegressionReportBuilder().build(result)
    assert report.status == "passed"
    assert report.summary
