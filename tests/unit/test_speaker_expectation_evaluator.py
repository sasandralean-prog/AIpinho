from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.speaker_expectation_evaluator import SpeakerExpectationEvaluator

def test_speaker_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="speaker", assertions={"ok": True})
    result = SpeakerExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
