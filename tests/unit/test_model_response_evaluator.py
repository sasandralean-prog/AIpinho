from aipinho.schemas.evaluation.evaluation_request import EvaluationRequest
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator


def _request(content, contract=None, safety=None, evidence=None, finish_reason="stop", purpose="chat"):
    return EvaluationRequest(
        model_response={"content": content, "status": "completed", "finish_reason": finish_reason, "real_inference": False},
        output_contract=contract or {"contract_type": "plain_text", "format": "text"},
        safety_envelope=safety or {"rules": ["no_tools", "no_files", "no_patch"]},
        evidence_context=evidence or [],
        purpose=purpose,
        include_trace=True,
    )


def test_model_response_evaluator_accepts_valid_response():
    result = ModelResponseEvaluator().evaluate(_request("Resposta segura."))
    assert result.status == "accepted"
    assert result.contract_valid is True
    assert result.safety_valid is True


def test_model_response_evaluator_needs_retry_for_invalid_json():
    result = ModelResponseEvaluator().evaluate(_request('{"findings":', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"]}))
    assert result.status == "needs_retry"
    assert "invalid_json" in result.violations
    assert result.retry_decision.should_retry is True


def test_model_response_evaluator_rejects_safety_violation():
    result = ModelResponseEvaluator().evaluate(_request("Executei o comando e apliquei o patch."))
    assert result.status == "rejected"
    assert "critical_safety_violation" in result.violations
    assert result.fallback_decision.should_fallback is True


def test_model_response_evaluator_needs_retry_for_truncation():
    result = ModelResponseEvaluator().evaluate(_request("texto", finish_reason="length"))
    assert result.status == "needs_retry"
    assert result.truncation_detected is True


def test_model_response_evaluator_rejects_missing_evidence():
    result = ModelResponseEvaluator().evaluate(_request('{"findings": [{"summary":"x"}], "limitations": []}', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"], "require_evidence": True}, evidence=[{"evidence_id": "ev1"}]))
    assert result.status == "rejected"
    assert any(item.startswith("missing_required_evidence") for item in result.violations)


def test_model_response_evaluator_is_deterministic_for_same_request():
    request = _request('{"findings":', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"]})
    a = ModelResponseEvaluator().evaluate(request)
    b = ModelResponseEvaluator().evaluate(request)
    assert a.status == b.status
    assert a.violations == b.violations
    assert a.score == b.score
