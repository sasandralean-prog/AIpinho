from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import RAGQueryRequest, RAGQueryResult
from aipinho.schemas.vision.contracts import VisionRAGQueryRequest
from aipinho.services.rag.vector.rag_vector_query_service import RAGVectorQueryService


class VisionRAGQueryService:
    def __init__(self) -> None:
        self.query_service = RAGVectorQueryService()

    def query(self, request: VisionRAGQueryRequest) -> RAGQueryResult:
        return self.query_service.query(
            RAGQueryRequest(
                query=request.query,
                namespace_id=request.namespace,
                top_k=request.top_k,
                use_global_context=False,
                include_context_bundle=True,
                include_trace=request.include_trace,
                metadata={"vision_rag_wrapper": True},
            )
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vision_rag_query", "namespaces": ["vision_rag", "ocr_rag"]}
