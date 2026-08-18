from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.policy_expectation_evaluator import PolicyExpectationEvaluator

def test_policy_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="policy", assertions={"ok": True})
    result = PolicyExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
