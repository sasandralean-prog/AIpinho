from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService


def test_capability_question_uses_canonical_truth(monkeypatch) -> None:
    monkeypatch.setattr(ChatService, "respond", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("generic chat must not answer capability truth")))
    response = CanonicalPublicChatService().respond(
        ChatRequest(message="Voce consegue executar tarefas e editar arquivos?", context=ChatContext(surface="api")),
        source_channel="api_chat",
    )

    assert response.operation_type == "capability_truth"
    assert "CAPABILITY_TRUTH_READY" in response.message
    assert "capability_truth" in response.policy


def test_plain_conversation_cannot_deny_governed_capabilities() -> None:
    response = CanonicalPublicChatService().respond(
        ChatRequest(message="Voce pode criar projeto?", context=ChatContext(surface="api")),
        source_channel="api_chat",
    )

    assert "Nao tenho capacidade de execucao de tarefas" not in response.message
    assert response.intent["intent_type"] == "capability_truth"
