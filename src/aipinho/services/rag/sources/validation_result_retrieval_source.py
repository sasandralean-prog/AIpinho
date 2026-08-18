from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalHit, RetrievalRequest
from aipinho.services.rag.citation_builder import CitationBuilder
from aipinho.services.validation.validation_store import ValidationStore


class ValidationResultRetrievalSource:
    source_id = "validation_results"

    def __init__(self, store: ValidationStore | None = None, citations: CitationBuilder | None = None) -> None:
        self.store = store or ValidationStore()
        self.citations = citations or CitationBuilder()

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalHit]:
        if not request.validation_id:
            return []
        result = self.store.get_result(request.validation_id)
        if result is None or not result.safe_to_display:
            return []
        finding_summary = "; ".join(
            f"{finding.severity}:{finding.title}" for finding in result.findings[:3] if finding.safe_to_display
        )
        excerpt = (
            f"Validation {result.status}; score={result.score}. "
            f"{finding_summary or 'No displayable findings.'}"
        )[: request.budget.max_hit_excerpt_chars]
        evidence_id = result.findings[0].finding_id if result.findings else None
        citation = self.citations.build(
            citation_type="validation_finding",
            source_id=self.source_id,
            source_type="validation_result",
            ref=result.validation_id,
            location=f"{result.validation_id}:result",
            section=result.target_type,
            evidence_id=evidence_id,
            excerpt=excerpt,
        )
        return [
            RetrievalHit(
                source_id=self.source_id,
                source_type="validation_result",
                title=f"Validation {result.validation_id}",
                excerpt=excerpt,
                citation=citation,
                source_ref=citation.source_ref,
                metadata={
                    "validation_id": result.validation_id,
                    "target_type": result.target_type,
                    "target_id": result.target_id,
                    "status": result.status,
                    "score": result.score,
                    "finding_count": len(result.findings),
                },
            )
        ]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "source": self.source_id, "read_only": True, "required_lookup": "validation_id"}
