import os

import pytest

from aipinho.schemas.rag.vector.contracts import EmbeddingRequest, RAGVectorHit, RerankRequest
from aipinho.services.rag.vector.embedding_provider_service import EmbeddingProviderService
from aipinho.services.rag.vector.reranker_provider_service import RerankerProviderService
from vector_rag_test_helpers import chunk, citation, source_ref


pytestmark = [pytest.mark.real_inference, pytest.mark.manual]


def _real_rag_runtime_enabled() -> bool:
    return os.environ.get("AIPINHO_ENABLE_REAL_RAG_RUNTIME_TESTS", "").lower() in {"1", "true", "yes", "on"}


@pytest.mark.skipif(not _real_rag_runtime_enabled(), reason="real llama-server RAG runtime smoke requires explicit opt-in")
def test_real_llama_server_embedding_and_reranker_smoke():
    embedding_result = EmbeddingProviderService().embed(EmbeddingRequest(chunks=[chunk(text="AIpinho vector RAG runtime smoke.")]))
    assert embedding_result.status == "ok"
    assert embedding_result.real_runtime_attempted is True
    assert embedding_result.deterministic_fallback_used is False
    assert embedding_result.embeddings

    hit = RAGVectorHit(
        namespace_id="coder_rag",
        chunk_id="runtime_chunk",
        text="AIpinho vector RAG runtime smoke.",
        score=0.1,
        source_ref=source_ref(),
        citation=citation(),
    )
    rerank_result = RerankerProviderService().rerank(RerankRequest(query="vector runtime smoke", hits=[hit], top_k=1))
    assert rerank_result.status == "ok"
    assert rerank_result.real_runtime_attempted is True
    assert rerank_result.deterministic_fallback_used is False
    assert rerank_result.hits
