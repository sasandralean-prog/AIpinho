from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import RAGQueryRequest, RoleRAGContext
from aipinho.services.rag.vector.rag_vector_query_service import RAGVectorQueryService


class RoleRAGContextBuilder:
    def __init__(self, query_service: RAGVectorQueryService | None = None) -> None:
        self.query_service = query_service or RAGVectorQueryService()

    def build(self, role_id: str, query: str, *, top_k: int = 5, use_global_context: bool = True) -> RoleRAGContext:
        result = self.query_service.query(RAGQueryRequest(query=query, role_id=role_id, top_k=top_k, use_global_context=use_global_context))
        return RoleRAGContext(role_id=role_id, query=query, result=result, safe_for_prompt_assembly=bool(result.context_bundle and result.context_bundle.safe_for_prompt_assembly))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_rag_context_builder"}
