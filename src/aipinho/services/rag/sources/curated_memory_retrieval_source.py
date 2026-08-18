from __future__ import annotations

from aipinho.schemas.memory.curated_memory import MemorySearchRequest
from aipinho.schemas.rag.retrieval_request import RetrievalHit, RetrievalRequest
from aipinho.services.memory.curated_memory_search_service import CuratedMemorySearchService
from aipinho.services.memory.memory_read_policy_service import MemoryReadPolicyService
from aipinho.services.rag.citation_builder import CitationBuilder


class CuratedMemoryRetrievalSource:
    source_id = "curated_memory"

    def __init__(self, search: CuratedMemorySearchService | None = None, read_policy: MemoryReadPolicyService | None = None, citations: CitationBuilder | None = None) -> None:
        self.search = search or CuratedMemorySearchService()
        self.read_policy = read_policy or MemoryReadPolicyService()
        self.citations = citations or CitationBuilder()

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalHit]:
        if not request.explicit or not self.read_policy.explicit_read_allowed():
            return []
        result = self.search.search(MemorySearchRequest(status="active", text=request.query, workspace=request.scope.workspace, limit=request.budget.max_hits_per_source))
        hits: list[RetrievalHit] = []
        for memory in result.results:
            excerpt = memory.summary or memory.text[: request.budget.max_hit_excerpt_chars]
            evidence_id = memory.evidence[0].evidence_id if memory.evidence else None
            citation = self.citations.build(citation_type="memory_id", source_id=self.source_id, source_type="curated_memory", ref=memory.memory_id, location=f"{memory.memory_id}:v{memory.version}", section=memory.kind, evidence_id=evidence_id, excerpt=excerpt)
            hits.append(RetrievalHit(source_id=self.source_id, source_type="curated_memory", title=memory.kind, excerpt=excerpt, citation=citation, source_ref=citation.source_ref, metadata={"memory_id": memory.memory_id, "version": memory.version}))
        return hits

    def status(self) -> dict[str, object]:
        return {"status": "ok", "source": self.source_id, "explicit_request_required": True, "auto_enabled": False}
