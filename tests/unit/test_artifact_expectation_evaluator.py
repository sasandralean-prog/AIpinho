from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.artifact_expectation_evaluator import ArtifactExpectationEvaluator

def test_artifact_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="artifact", assertions={"ok": True})
    result = ArtifactExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
