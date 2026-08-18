from __future__ import annotations

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.semantic_runtime.semantic_intent_resolution_service import SemanticIntentResolutionService


class StaticConversationProvider:
    def respond(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            response_id="chat_static",
            session_id=request.session_id,
            status="ok",
            operation_type="conversation",
            message="2 + 2 é 4.",
            intent={"intent_type": "conversation", "requires_task": False},
            policy={"allowed_actions": [], "safe_to_execute": False},
        )


class ExplodingConversationProvider:
    def respond(self, request: ChatRequest) -> ChatResponse:
        raise AssertionError("meta-conversation must not call the legacy conversation provider")


class TimeoutModelInvocation:
    def invoke(self, request) -> ModelResponse:
        return ModelResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            provider_id=request.provider_id,
            status="error",
            content="",
            finish_reason="timeout",
            real_inference=False,
            warnings=["stderr captured during model process"],
        )


def test_conversation_can_answer_text_without_operational_actions() -> None:
    response = CanonicalPublicChatService(chat_service=StaticConversationProvider()).respond(
        ChatRequest(message="Quanto é 2+2?"),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    assert response.operation_type == "conversation"
    assert response.intent["intent_type"] == "conversation"
    assert response.message == "2 + 2 é 4."
    assert response.task_id is None
    assert response.approval_id is None
    assert response.policy["canonical_lifecycle"]["speaker_can_claim_success"] is False


def test_meta_conversation_does_not_become_workspace_analysis() -> None:
    response = CanonicalPublicChatService(chat_service=ExplodingConversationProvider()).respond(
        ChatRequest(message="Agora explique por que você falhou na primeira resposta."),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    assert response.operation_type == "conversation"
    assert response.intent["intent_type"] == "conversation_self_diagnosis"
    assert response.task_id is None
    assert response.approval_id is None
    assert "workspace_analysis_readonly" not in response.intent.values()
    assert "nao na classificacao de intent" in response.message or "nao a uma promocao operacional" in response.message


def test_meta_conversation_rejects_false_intent_confusion_premise() -> None:
    response = CanonicalPublicChatService(chat_service=ExplodingConversationProvider()).respond(
        ChatRequest(message="Foi uma pergunta simples de matemática básica, como você confundiu o intent?"),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    assert response.operation_type == "conversation"
    assert response.intent["intent_type"] == "conversation_self_diagnosis"
    assert "Nao ha evidencia de confusao de intent" in response.message
    assert response.task_id is None


def test_meta_classification_correction_stays_conversational() -> None:
    decision = SemanticIntentResolutionService().resolve(
        "Você classificou erroneamente a última mensagem. Era apenas conversation.",
        source_channel="unit",
    )

    assert decision.intent_type == "conversation_self_diagnosis"
    assert decision.operation_type == "conversation"
    assert decision.requires_task is False
    assert decision.side_effect_requested is False


def test_conversation_model_failure_uses_runtime_model_reason_codes() -> None:
    response = ChatService(model_invocation_service=TimeoutModelInvocation()).respond(
        ChatRequest(message="Quanto é 2+2?"),
    )

    assert response.status == "degraded"
    assert response.intent["intent_type"] == "conversation"
    assert "nao na classificacao de intent" in response.message
    assert "MODEL_TIMEOUT" in response.model_warnings
    assert "STDERR_CAPTURED" in response.model_warnings
    assert "EMPTY_OUTPUT" in response.model_warnings
    assert "CONVERSATION_MODEL_UNAVAILABLE" in response.model_warnings
    assert response.task_id is None
