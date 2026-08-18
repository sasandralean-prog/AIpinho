from __future__ import annotations

import hashlib

from aipinho.schemas.rag.retrieval_request import Citation, CitationType, SourceRef


class CitationBuilder:
    def build(
        self,
        *,
        citation_type: CitationType,
        source_id: str,
        source_type: str,
        ref: str,
        excerpt: str,
        location: str | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        section: str | None = None,
        evidence_id: str | None = None,
    ) -> Citation:
        source_ref = SourceRef(source_id=source_id, source_type=source_type, ref=ref, location=location, content_hash=self._hash(excerpt))
        return Citation(citation_type=citation_type, source_ref=source_ref, excerpt=excerpt[:500], line_start=line_start, line_end=line_end, section=section, evidence_id=evidence_id)

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "citation_builder", "citation_required": True}
