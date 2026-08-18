from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import RAGVectorHit


class RAGCitationValidator:
    def validate_hits(self, hits: list[RAGVectorHit]) -> dict[str, object]:
        blocked: list[str] = []
        for hit in hits:
            if not hit.citation:
                blocked.append("missing_citation")
            if not hit.source_ref:
                blocked.append("missing_source_ref")
            elif hit.citation.source_ref.ref != hit.source_ref.ref:
                blocked.append("citation_source_ref_mismatch")
        return {"valid": not blocked, "status": "ok" if not blocked else "blocked", "blocked_reasons": list(dict.fromkeys(blocked))}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_citation_validator", "citation_required": True}
