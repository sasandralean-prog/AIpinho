from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalContextBundle, RetrievalHit, RetrievalRequest
from aipinho.services.rag.evidence_bundle_builder import EvidenceBundleBuilder
from aipinho.services.rag.source_ref_validator import SourceRefValidator


class RetrievalContextBuilder:
    def __init__(self, evidence_builder: EvidenceBundleBuilder | None = None, validator: SourceRefValidator | None = None) -> None:
        self.evidence_builder = evidence_builder or EvidenceBundleBuilder()
        self.validator = validator or SourceRefValidator()

    def build(self, request: RetrievalRequest, hits: list[RetrievalHit], retrieval_id: str | None = None, warnings: list[str] | None = None) -> RetrievalContextBundle:
        warnings = list(warnings or [])
        blocked: list[str] = []
        valid_hits: list[RetrievalHit] = []
        for hit in hits:
            check = self.validator.validate_citation(hit.citation)
            if not check["valid"]:
                blocked.extend(check["blocked_reasons"])
                continue
            valid_hits.append(hit)
        evidence = self.evidence_builder.build(valid_hits)
        if not evidence.valid:
            blocked.extend(evidence.blocked_reasons)
        context_text = "\n\n".join(f"[{index+1}] {hit.excerpt}\nCitation: {hit.citation.citation_id if hit.citation else 'missing'}" for index, hit in enumerate(valid_hits))
        status = "blocked" if blocked and not valid_hits else "found" if valid_hits else "no_results"
        return RetrievalContextBundle(
            retrieval_id=retrieval_id,
            status=status,
            query=request.query,
            hits=valid_hits,
            citations=[hit.citation for hit in valid_hits if hit.citation],
            evidence_bundle=evidence,
            budget=request.budget,
            source_refs=[hit.source_ref for hit in valid_hits if hit.source_ref],
            scope=request.scope,
            safe_for_prompt_assembly=bool(valid_hits and not blocked),
            context_text=context_text,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=list(dict.fromkeys(blocked)),
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_context_builder", "reject_uncited_context": True}
