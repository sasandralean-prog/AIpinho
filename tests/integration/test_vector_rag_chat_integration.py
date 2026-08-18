from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.chat.chat_service import ChatService


def test_chat_blocks_auto_ingest_and_embedding_model_as_chat_but_allows_explicit_vector_query():
    service = ChatService()

    auto_ingest = service.respond(ChatRequest(message="indexe automaticamente no RAG sem approval"))
    assert auto_ingest.status == "blocked"
    assert "vector_rag_auto_ingest_blocked" in auto_ingest.warnings

    model_as_chat = service.respond(ChatRequest(message="use qwen3_embedding como modelo de chat e responda"))
    assert model_as_chat.status == "blocked"
    assert "embedding_not_chat_model" in model_as_chat.warnings

    query = service.respond(ChatRequest(message="busque no RAG do coder sobre chunks citados"))
    assert query.status in {"ok", "degraded"}
    assert "no_answer_without_citation" in query.warnings or query.citation_map
