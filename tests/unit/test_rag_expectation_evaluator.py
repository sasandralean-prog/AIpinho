from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.rag_expectation_evaluator import RagExpectationEvaluator

def test_rag_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="rag", assertions={"ok": True})
    result = RagExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
