import inspect

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.chat.chat_service import ChatService


def test_canonical_public_chat_uses_chat_service_only_inside_conversation_provider() -> None:
    respond_source = inspect.getsource(CanonicalPublicChatService.respond)
    conversation_source = inspect.getsource(CanonicalPublicChatService._conversation_response)
    assert "self.chat_service.respond" not in respond_source
    assert "self.chat_service.respond" in conversation_source


def test_planning_readonly_does_not_call_legacy_permission_grant(monkeypatch) -> None:
    from aipinho.services.chat import chat_permission_grant_service

    def fail_grant(*_args, **_kwargs):
        raise AssertionError("legacy ChatPermissionGrantService must not classify read-only planning")

    monkeypatch.setattr(chat_permission_grant_service.ChatPermissionGrantService, "handle", fail_grant)
    response = CanonicalPublicChatService().respond(
        ChatRequest(message="Somente planejamento textual. Nao criar grant. product_planning_readonly"),
        source_channel="api_chat",
    )

    assert response.operation_type == "product_planning_readonly"
    assert response.approval_id is None


def test_chat_service_remains_content_provider_for_plain_conversation() -> None:
    response = CanonicalPublicChatService(chat_service=ChatService()).respond(
        ChatRequest(message="Ola, responda de forma breve."),
        source_channel="api_chat",
    )

    assert response.operation_type == "conversation"
    assert response.governance_lifecycle["intent"]["intent_type"] == "conversation"
    assert response.approval_id is None
