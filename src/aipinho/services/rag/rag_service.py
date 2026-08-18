from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalRequest
from aipinho.services.rag.retrieval_service import RetrievalService


class RagService:
    def __init__(self, retrieval: RetrievalService | None = None) -> None:
        self.retrieval = retrieval or RetrievalService()

    def retrieve(self, request: RetrievalRequest):
        return self.retrieval.retrieve(request)

    def status(self) -> dict[str, object]:
        status = self.retrieval.status()
        return {
            **status,
            "service": "rag",
            "mode": "governed_read_only",
            "query_enabled": True,
            "ingest_enabled": False,
            "vectorstore_enabled": False,
            "embeddings_enabled": False,
        }
