from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import Citation, SourceRef


class SourceRefValidator:
    def validate_source_ref(self, source_ref: SourceRef | None) -> dict[str, object]:
        reasons: list[str] = []
        if source_ref is None:
            reasons.append("source_ref_missing")
        else:
            if not source_ref.source_id:
                reasons.append("source_id_missing")
            if not source_ref.ref:
                reasons.append("source_ref_location_missing")
        return {"valid": not reasons, "status": "ok" if not reasons else "blocked", "blocked_reasons": reasons}

    def validate_citation(self, citation: Citation | None) -> dict[str, object]:
        reasons: list[str] = []
        if citation is None:
            reasons.append("citation_missing")
            return {"valid": False, "status": "blocked", "blocked_reasons": reasons}
        ref_check = self.validate_source_ref(citation.source_ref)
        reasons.extend(ref_check["blocked_reasons"])
        if not citation.excerpt:
            reasons.append("citation_excerpt_missing")
        return {"valid": not reasons, "status": "ok" if not reasons else "blocked", "blocked_reasons": reasons}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "source_ref_validator"}
