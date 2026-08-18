from aipinho.services.rag.vector.rag_chunk_validator import RAGChunkValidator

from vector_rag_test_helpers import chunk


def test_rag_chunk_validator_requires_citation_and_blocks_secret_like_content():
    validator = RAGChunkValidator()
    assert validator.validate(chunk())["valid"] is True

    secret_chunk = chunk(text="api_key=should_not_enter_vector_index")
    result = validator.validate(secret_chunk)
    assert result["status"] == "blocked"
    assert "secret_or_sensitive_content_blocked" in result["blocked_reasons"]
