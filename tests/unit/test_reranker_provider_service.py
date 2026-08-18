from aipinho.schemas.rag.vector.contracts import RAGVectorHit, RerankRequest
from aipinho.services.rag.vector.llama_server_runtime_service import LlamaServerResponse
from aipinho.services.rag.vector.reranker_provider_service import RerankerProviderService

from vector_rag_test_helpers import citation, source_ref


class FakeRerankerRuntime:
    def __init__(self, response: LlamaServerResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def rerank(self, *, query: str, documents: list[str], model_id: str, top_k: int) -> LlamaServerResponse:
        self.calls.append({"query": query, "documents": documents, "model_id": model_id, "top_k": top_k})
        return self.response

    def status(self) -> dict[str, object]:
        return {"reranker": {"reachable": self.response.status == "ok", "fake_provider": True}}


def test_reranker_uses_real_runtime_when_available():
    hit = RAGVectorHit(namespace_id="coder_rag", chunk_id="chunk_1", text="quality gate and patch preview", score=0.2, source_ref=source_ref(), citation=citation())
    runtime = FakeRerankerRuntime(LlamaServerResponse(status="ok", data=[(0, 0.91)], endpoint="/v1/rerank"))

    result = RerankerProviderService(runtime=runtime).rerank(RerankRequest(query="quality gate", hits=[hit]))

    assert result.status == "ok"
    assert result.model_id == "qwen3_reranker_4b_q5_k_m"
    assert result.real_runtime_attempted is True
    assert result.deterministic_fallback_used is False
    assert result.hits[0].chunk_id == "chunk_1"
    assert result.hits[0].score == 0.91
    assert runtime.calls[0]["model_id"] == "qwen3_reranker_4b_q5_k_m"


def test_reranker_preserves_hits_and_citations_with_explicit_fallback():
    hit = RAGVectorHit(namespace_id="coder_rag", chunk_id="chunk_1", text="quality gate and patch preview", score=0.2, source_ref=source_ref(), citation=citation())
    runtime = FakeRerankerRuntime(LlamaServerResponse(status="error", warnings=["reranker_server_unreachable"]))

    result = RerankerProviderService(runtime=runtime).rerank(RerankRequest(query="quality gate", hits=[hit]))

    assert result.status == "ok"
    assert result.model_id == "qwen3_reranker_4b_q5_k_m"
    assert result.real_runtime_attempted is True
    assert result.deterministic_fallback_used is True
    assert result.hits[0].chunk_id == "chunk_1"
    assert result.hits[0].citation.citation_type == "file_line_range"
    assert "reranker_runtime_fallback_used" in result.warnings
