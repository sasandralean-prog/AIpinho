from aipinho.services.regression.golden_expectation_service import GoldenExpectationService
from aipinho.services.regression.regression_case_service import RegressionCaseService

def test_case_creation_keeps_expectations():
    expectation = GoldenExpectationService().create("policy", {"write_allowed": False})
    case = RegressionCaseService().create("unit", "policy", [expectation])
    assert case.expectations[0].assertions["write_allowed"] is False
