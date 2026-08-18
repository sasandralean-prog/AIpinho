from aipinho.services.regression.regression_suite_service import RegressionSuiteService

def test_core_and_legacy_suites_load():
    service = RegressionSuiteService()
    assert service.get("core_regression_suite").cases
    assert service.get("legacy_bug_regression_suite").cases
