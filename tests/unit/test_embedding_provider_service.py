from aipinho.schemas.rag.vector.contracts import EmbeddingRequest
from aipinho.services.rag.vector.embedding_provider_service import EmbeddingProviderService
from aipinho.services.rag.vector.llama_server_runtime_service import LlamaServerResponse

from vector_rag_test_helpers import chunk


class FakeEmbeddingRuntime:
    def __init__(self, response: LlamaServerResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def embed(self, texts: list[str], *, model_id: str) -> LlamaServerResponse:
        self.calls.append({"texts": texts, "model_id": model_id})
        return self.response

    def status(self) -> dict[str, object]:
        return {"embedding": {"reachable": self.response.status == "ok", "fake_provider": True}}


def test_embedding_provider_uses_real_runtime_when_available():
    runtime = FakeEmbeddingRuntime(LlamaServerResponse(status="ok", data=[[0.1, 0.2, 0.3]], endpoint="/v1/embeddings"))
    result = EmbeddingProviderService(runtime=runtime).embed(EmbeddingRequest(chunks=[chunk()]))

    assert result.status == "ok"
    assert result.model_id == "qwen3_embedding_4b_q5_k_m"
    assert result.real_runtime_attempted is True
    assert result.deterministic_fallback_used is False
    assert result.embeddings
    assert runtime.calls[0]["model_id"] == "qwen3_embedding_4b_q5_k_m"


def test_embedding_provider_falls_back_explicitly_when_runtime_unavailable():
    runtime = FakeEmbeddingRuntime(LlamaServerResponse(status="error", warnings=["embedding_server_unreachable"]))
    result = EmbeddingProviderService(runtime=runtime).embed(EmbeddingRequest(chunks=[chunk()]))

    assert result.status == "ok"
    assert result.model_id == "qwen3_embedding_4b_q5_k_m"
    assert result.real_runtime_attempted is True
    assert result.deterministic_fallback_used is True
    assert result.embeddings
    assert "embedding_runtime_fallback_used" in result.warnings
