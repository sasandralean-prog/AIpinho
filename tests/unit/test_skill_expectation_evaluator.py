from aipinho.schemas.regression.contracts import GoldenExpectation
from aipinho.services.regression.evaluators.skill_expectation_evaluator import SkillExpectationEvaluator

def test_skill_expectation_evaluator_exact_match():
    expectation = GoldenExpectation(expectation_type="skill", assertions={"ok": True})
    result = SkillExpectationEvaluator().evaluate(expectation, {"ok": True})
    assert result.status == "passed"
