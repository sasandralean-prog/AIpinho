from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.services.chat.chat_manual_inference_service import ChatManualInferenceService
from aipinho.services.chat.chat_service import ChatService


def test_normal_chat_does_not_use_real_model_even_if_user_asks():
    response = ChatService().respond(ChatRequest(message="Use inferencia real com llama.cpp agora"))
    assert response.real_inference is False
    assert "nao inicia processo local" in response.message.lower()


def test_manual_chat_requires_explicit_opt_in_and_enabled_policy():
    response = ChatManualInferenceService().run(ManualChatInferenceRequest(message="Ola"))
    assert response.status == "blocked"
    assert response.process_started is False
    assert "request_opt_in_missing" in response.warnings
