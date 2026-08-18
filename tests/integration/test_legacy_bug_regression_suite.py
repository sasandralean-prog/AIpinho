from aipinho.services.regression.regression_suite_service import RegressionSuiteService

def test_legacy_bug_suite_contains_negated_patch_case():
    suite=RegressionSuiteService().get("legacy_bug_regression_suite")
    assert any(case.case_id=="patch_word_is_not_patch_request_when_negated" for case in suite.cases)
