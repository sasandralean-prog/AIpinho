from aipinho.services.regression.golden_expectation_service import GoldenExpectationService

def test_golden_expectation_records_assertions():
    expectation = GoldenExpectationService().create("intent", {"requires_task": False})
    assert expectation.expectation_type == "intent"
    assert expectation.assertions["requires_task"] is False
