from aipinho.services.regression.golden_expectation_service import GoldenExpectationService
from aipinho.services.regression.regression_case_service import RegressionCaseService
from aipinho.services.regression.regression_runner_service import RegressionRunnerService

def test_runner_passes_matching_expectations():
    expectation = GoldenExpectationService().create("policy", {"write_allowed": False})
    case = RegressionCaseService().create("unit run", "policy", [expectation])
    result = RegressionRunnerService().run_case(case)
    assert result.status == "passed"
    assert result.side_effects_performed is False
