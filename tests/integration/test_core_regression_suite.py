from aipinho.services.regression.regression_suite_service import RegressionSuiteService

def test_core_suite_contains_required_cases():
    suite=RegressionSuiteService().get("core_regression_suite")
    ids={case.case_id for case in suite.cases}
    assert {"greeting_not_task","self_analysis_not_workspace","patch_read_only_blocked","maintenance_no_autonomous_apply"} <= ids
