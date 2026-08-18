from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.patch_expectation_evaluator import PatchExpectationEvaluator

def test_patch_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="patch", assertions={"ok": True})
    result = PatchExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
