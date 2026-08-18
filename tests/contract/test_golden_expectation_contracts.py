from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.expectation_evaluator import ExpectationEvaluator

def test_exact_policy_drift_fails():
    expectation = GoldenExpectation(expectation_type="policy", assertions={"write_allowed": False}, failure_severity="critical")
    result = ExpectationEvaluator().evaluate(expectation, {"write_allowed": True})
    assert result.status == "failed"
    assert result.severity == "critical"
