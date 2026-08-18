from aipinho.schemas.evaluation.evaluation_finding import EvaluationFinding
from aipinho.schemas.evaluation.evaluation_request import EvaluationRequest
from aipinho.schemas.evaluation.evaluation_result import EvaluationResult
from aipinho.schemas.evaluation.fallback_decision import FallbackDecision
from aipinho.schemas.evaluation.retry_decision import RetryDecision
from aipinho.schemas.evaluation.safety_violation import SafetyViolation


def test_evaluation_request_requires_model_response():
    request = EvaluationRequest(model_response={"content": "ok"})
    assert request.purpose == "chat"
    assert request.model_response["content"] == "ok"


def test_evaluation_result_contract_defaults_are_safe():
    result = EvaluationResult(evaluation_id="ev", status="rejected")
    assert result.contract_valid is False
    assert result.safety_valid is False
    assert result.fallback_decision.fallback_type == "none"


def test_evaluation_finding_contract():
    finding = EvaluationFinding(code="claims_unseen_files", message="unseen")
    assert finding.severity == "medium"
    assert finding.critical is False


def test_safety_violation_contract_defaults_critical():
    violation = SafetyViolation(violation_id="secret_leak", type="secret", message="secret")
    assert violation.critical is True
    assert violation.severity == "critical"


def test_retry_and_fallback_decision_contracts():
    retry = RetryDecision(should_retry=True, reason="invalid_json", strategy="ask_for_json_only")
    fallback = FallbackDecision(should_fallback=True, fallback_type="safe_error", reason="invalid_json")
    assert retry.should_retry is True
    assert fallback.should_fallback is True
