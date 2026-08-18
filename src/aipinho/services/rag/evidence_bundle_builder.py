from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import EvidenceBundle, RetrievalHit
from aipinho.services.rag.source_ref_validator import SourceRefValidator


class EvidenceBundleBuilder:
    def __init__(self, validator: SourceRefValidator | None = None) -> None:
        self.validator = validator or SourceRefValidator()

    def build(self, hits: list[RetrievalHit]) -> EvidenceBundle:
        citations = []
        blocked: list[str] = []
        for hit in hits:
            check = self.validator.validate_citation(hit.citation)
            if not check["valid"]:
                blocked.extend(check["blocked_reasons"])
                continue
            citations.append(hit.citation)
        return EvidenceBundle(status="valid" if not blocked else "blocked", citations=citations, evidence_count=len(citations), valid=not blocked, blocked_reasons=list(dict.fromkeys(blocked)))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "evidence_bundle_builder"}
