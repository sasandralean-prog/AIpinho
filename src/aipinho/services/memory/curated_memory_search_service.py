from __future__ import annotations

from aipinho.schemas.memory.curated_memory import MemorySearchRequest, MemorySearchResult
from aipinho.services.memory.curated_memory_store import CuratedMemoryStore


class CuratedMemorySearchService:
    def __init__(self, store: CuratedMemoryStore | None = None) -> None:
        self.store = store or CuratedMemoryStore()

    def search(self, request: MemorySearchRequest) -> MemorySearchResult:
        results = self.store.list_memories(
            status=request.status,
            kind=request.kind,
            scope=request.scope,
            workspace=request.workspace,
            source_type=request.source_type,
            confidence=request.confidence,
            risk=request.risk,
            text=request.text,
            tag=request.tag,
            limit=request.limit,
        )
        return MemorySearchResult(status="ok", results=results)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "search_mode": "deterministic", "vectorstore_enabled": False, "embeddings_enabled": False, "rag_enabled": False}
