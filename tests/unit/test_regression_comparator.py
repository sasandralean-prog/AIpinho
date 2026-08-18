from aipinho.services.regression.golden_expectation_service import GoldenExpectationService
from aipinho.services.regression.regression_comparator import RegressionComparator

def test_comparator_marks_policy_drift_as_failure():
    expectation = GoldenExpectationService().create("policy", {"write_allowed": False})
    results, failures = RegressionComparator().compare([expectation], {"write_allowed": True})
    assert results[0].status == "failed"
    assert failures
