from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.maintenance_expectation_evaluator import MaintenanceExpectationEvaluator

def test_maintenance_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="maintenance", assertions={"ok": True})
    result = MaintenanceExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
