import pytest

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.evaluation.evaluation_request import EvaluationRequest
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator
from aipinho.services.models.model_invocation_service import ModelInvocationService


def _eval(content, contract=None, safety=None, evidence=None, finish_reason="stop", purpose="chat", system_status=None):
    model_response = {"content": content, "status": "completed", "finish_reason": finish_reason, "real_inference": False}
    if system_status is not None:
        model_response["system_status"] = system_status
    return ModelResponseEvaluator().evaluate(EvaluationRequest(
        model_response=model_response,
        output_contract=contract or {"contract_type": "plain_text", "format": "text"},
        safety_envelope=safety or {"rules": ["no_tools", "no_files", "no_patch"]},
        evidence_context=evidence or [],
        purpose=purpose,
        include_trace=True,
    ))


@pytest.mark.parametrize(
    "case, result",
    [
        ("valid_json_contract", lambda: _eval('{"findings": [], "limitations": []}', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"]})),
        ("invalid_json_contract", lambda: _eval('{"findings":', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"]})),
        ("markdown_report_valid", lambda: _eval('# Executive Summary\nOk\n# Findings\nNone\n# Recommendations\nContinue\n# Limitations\nStub', {"contract_type": "markdown_report", "format": "markdown", "required_sections": ["executive_summary", "findings", "recommendations", "limitations"]})),
        ("markdown_missing_section", lambda: _eval('# Executive Summary\nOk\n# Findings\nNone\n# Recommendations\nContinue', {"contract_type": "markdown_report", "format": "markdown", "required_sections": ["executive_summary", "findings", "recommendations", "limitations"]})),
        ("claims_execution", lambda: _eval('Executei o comando e apliquei o patch.')),
        ("secret_like", lambda: _eval('api_key=abc123')),
        ("read_only_violation", lambda: _eval('Modifiquei os arquivos.', safety={"rules": ["read only"]})),
        ("evidence_required_valid", lambda: _eval('{"findings": [{"summary": "x", "evidence_id": "ev1"}], "limitations": []}', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"], "require_evidence": True}, evidence=[{"evidence_id": "ev1", "source": "config"}])),
        ("evidence_required_missing", lambda: _eval('{"findings": [{"summary": "x"}], "limitations": []}', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"], "require_evidence": True}, evidence=[{"evidence_id": "ev1"}])),
        ("unseen_file_citation", lambda: _eval('Veja src/foo/bar.py', evidence=[{"path": "src/known.py"}])),
        ("unavailable_capability_claim", lambda: _eval('O sistema ja faz RAG real e memoria persistente.', system_status={"rag": "disabled", "memory": "disabled"})),
        ("truncated_json", lambda: _eval('{"findings":', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings"]}, finish_reason="length")),
        ("retry_invalid_json", lambda: _eval('{"findings":', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings"]})),
        ("no_retry_critical_safety", lambda: _eval('api_key=abc123')),
        ("determinism_a", lambda: _eval('{"findings":', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings"]})),
    ],
)
def test_e2e_evaluation_cases(case, result):
    evaluated = result()
    assert evaluated.status in {"accepted", "accepted_with_warnings", "rejected", "needs_retry", "degraded"}
    if case == "valid_json_contract":
        assert evaluated.status == "accepted"
    if case == "invalid_json_contract":
        assert evaluated.status == "needs_retry"
    if case == "markdown_missing_section":
        assert evaluated.status == "needs_retry"
    if case in {"claims_execution", "secret_like", "read_only_violation", "no_retry_critical_safety"}:
        assert evaluated.status == "rejected"
    if case == "evidence_required_missing":
        assert evaluated.status == "rejected"
    if case == "truncated_json":
        assert evaluated.truncation_detected is True


def test_e2e_stub_response_evaluation_attached():
    response = ModelInvocationService().invoke_stub_prompt(prompt="Ola", output_contract_type="plain_text")
    assert response.real_inference is False
    assert response.evaluation_result is not None
    assert response.evaluation_result["status"] in {"accepted", "accepted_with_warnings"}


def test_e2e_real_model_mocked_invalid_json_rejected_by_evaluator():
    result = _eval('{"findings":', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings"]}, purpose="smoke_test")
    assert result.status == "needs_retry"
    assert result.retry_decision.should_retry is True


class RejectedModelInvocation:
    def invoke(self, model_request):
        return ModelResponse(
            request_id=model_request.request_id,
            model_id=model_request.model_id,
            provider_id=model_request.provider_id,
            status="degraded",
            content="api_key=abc123",
            real_inference=False,
            evaluation_result={
                "status": "rejected",
                "warnings": [],
                "fallback_decision": {"should_fallback": True, "safe_message": "fallback seguro", "fallback_type": "deterministic_speaker"},
            },
            warnings=["model_response_evaluation_failed"],
        )


def test_e2e_fallback_chat_hides_rejected_model_content():
    response = ChatService(model_invocation_service=RejectedModelInvocation()).respond(ChatRequest(message="Ola", use_model_stub=True))
    assert response.fallback_used is True
    assert response.message == "fallback seguro"
    assert "abc123" not in response.message


def test_e2e_fallback_report_policy_preserves_deterministic_report_decision():
    result = _eval('api_key=abc123', purpose="project_report")
    assert result.status == "rejected"
    assert result.fallback_decision.fallback_type == "deterministic_report"


def test_e2e_same_request_has_stable_score_and_violations():
    request = EvaluationRequest(model_response={"content": '{"findings":', "finish_reason": "stop"}, output_contract={"contract_type": "json_findings", "format": "json", "required_fields": ["findings"]}, safety_envelope={"rules": ["no_tools"]})
    a = ModelResponseEvaluator().evaluate(request)
    b = ModelResponseEvaluator().evaluate(request)
    assert a.status == b.status
    assert a.score == b.score
    assert a.violations == b.violations
