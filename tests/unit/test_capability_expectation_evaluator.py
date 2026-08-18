from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.capability_expectation_evaluator import CapabilityExpectationEvaluator

def test_capability_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="capability", assertions={"ok": True})
    result = CapabilityExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
