from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import RerankRequest, RerankResult
from aipinho.services.rag.vector.reranker_provider_service import RerankerProviderService


class RAGRerankService:
    def __init__(self, provider: RerankerProviderService | None = None) -> None:
        self.provider = provider or RerankerProviderService()

    def rerank(self, request: RerankRequest) -> RerankResult:
        return self.provider.rerank(request)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_rerank", "preserve_citations": True}
