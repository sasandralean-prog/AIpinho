from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.event_contract_expectation_evaluator import EventContractExpectationEvaluator

def test_event_contract_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="event_contract", assertions={"ok": True})
    result = EventContractExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
