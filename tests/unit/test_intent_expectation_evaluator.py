from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.intent_expectation_evaluator import IntentExpectationEvaluator

def test_intent_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="intent", assertions={"ok": True})
    result = IntentExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
