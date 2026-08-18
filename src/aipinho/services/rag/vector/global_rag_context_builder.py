from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import GlobalRAGContext, RAGQueryRequest
from aipinho.services.rag.vector.rag_vector_query_service import RAGVectorQueryService


class GlobalRAGContextBuilder:
    def __init__(self, query_service: RAGVectorQueryService | None = None) -> None:
        self.query_service = query_service or RAGVectorQueryService()

    def build(self, query: str, *, top_k: int = 5) -> GlobalRAGContext:
        result = self.query_service.query(RAGQueryRequest(query=query, namespace_id="global_ecosystem", top_k=top_k, use_global_context=False))
        return GlobalRAGContext(query=query, result=result, supporting_context=True)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "global_rag_context_builder", "supporting_context_only": True}
