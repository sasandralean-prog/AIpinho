from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.mobile_sync_expectation_evaluator import MobileSyncExpectationEvaluator

def test_mobile_sync_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="mobile_sync", assertions={"ok": True})
    result = MobileSyncExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
