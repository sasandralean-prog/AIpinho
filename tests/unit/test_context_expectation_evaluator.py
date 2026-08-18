from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.context_expectation_evaluator import ContextExpectationEvaluator

def test_context_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="context", assertions={"ok": True})
    result = ContextExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
