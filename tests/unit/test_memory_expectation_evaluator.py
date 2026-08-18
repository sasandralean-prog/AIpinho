from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.memory_expectation_evaluator import MemoryExpectationEvaluator

def test_memory_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="memory", assertions={"ok": True})
    result = MemoryExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
