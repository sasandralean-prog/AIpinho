import pytest
from pydantic import ValidationError

from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.schemas.chat.manual_chat_inference_response import ManualChatInferenceResponse


def test_manual_chat_inference_request_defaults_are_safe():
    request = ManualChatInferenceRequest(message="Ola")
    assert request.allow_real_inference is False
    assert request.operator_confirmed is False
    assert request.profile_id == "llama_cpp_manual_small"


def test_manual_chat_inference_request_requires_message():
    with pytest.raises(ValidationError):
        ManualChatInferenceRequest(message="   ")


def test_manual_chat_inference_response_contract_has_safety_metadata():
    response = ManualChatInferenceResponse(status="blocked", message="bloqueado")
    assert response.real_inference is False
    assert response.process_started is False
    assert response.fallback.rejected_model_content_hidden is True
