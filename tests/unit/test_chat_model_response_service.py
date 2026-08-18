from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.chat.chat_model_response_service import ChatModelResponseService


def test_chat_model_response_accepts_evaluated_model_output():
    response = ModelResponse(request_id="r", model_id="m", provider_id="p", status="completed", content="Resposta segura.", real_inference=True, evaluation_result={"status": "accepted", "score": 1.0, "warnings": [], "violations": [], "fallback_decision": {"should_fallback": False}})
    converted = ChatModelResponseService().convert(response, profile_id="profile")
    assert converted["status"] == "ok"
    assert converted["message"] == "Resposta segura."
    assert converted["model"].real_inference is True


def test_chat_model_response_hides_rejected_output():
    response = ModelResponse(request_id="r", model_id="m", provider_id="p", status="degraded", content="token=abc123", real_inference=True, warnings=["bad"], evaluation_result={"status": "rejected", "violations": ["critical_safety_violation"], "warnings": [], "fallback_decision": {"should_fallback": True}})
    converted = ChatModelResponseService().convert(response, profile_id="profile")
    assert converted["fallback"].fallback_used is True
    assert "abc123" not in converted["message"]
