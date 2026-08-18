from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.model_routing_expectation_evaluator import ModelRoutingExpectationEvaluator

def test_model_routing_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="model_routing", assertions={"ok": True})
    result = ModelRoutingExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
