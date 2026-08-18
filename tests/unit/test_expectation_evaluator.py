from aipinho.services.regression.golden_expectation_service import GoldenExpectationService
from aipinho.services.regression.expectation_evaluator import ExpectationEvaluator

def test_evaluator_passes_exact_match():
    expectation = GoldenExpectationService().create("speaker", {"cannot_claim_fixed_without_event": True})
    result = ExpectationEvaluator().evaluate(expectation, {"cannot_claim_fixed_without_event": True})
    assert result.status == "passed"
