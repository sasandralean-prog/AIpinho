from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.chat.chat_service import ChatService


def test_chat_image_analysis_without_source_ref_needs_clarification():
    response = ChatService().respond(ChatRequest(message="Analise esta imagem para mim"))

    assert response.status == "needs_clarification"
    assert "source_ref_required" in response.warnings
    assert "raw" not in response.message.lower()


def test_chat_blocks_image_to_memory_auto_save():
    response = ChatService().respond(ChatRequest(message="Guarde esta imagem na memoria"))

    assert response.status == "blocked"
    assert "raw_image_memory_blocked" in response.warnings


def test_chat_blocks_vision_rag_auto_ingest():
    response = ChatService().respond(ChatRequest(message="Indexe esta imagem no vision rag automaticamente sem approval"))

    assert response.status == "blocked"
    assert "vision_rag_auto_ingest_blocked" in response.warnings


def test_chat_multimodal_model_is_not_chat_model():
    response = ChatService().respond(ChatRequest(message="Use llava como chat para responder"))

    assert response.status == "blocked"
    assert "multimodal_model_not_chat_model" in response.warnings
    assert response.real_inference is False


def test_chat_vision_status_is_human_and_not_raw_dump():
    response = ChatService().respond(ChatRequest(message="Qual o status do OCR e vision?"))

    assert response.status in {"ok", "degraded"}
    assert "Vision/OCR governado" in response.message
    assert "raw" in response.message.lower()
    assert response.raw_debug_ref is None
