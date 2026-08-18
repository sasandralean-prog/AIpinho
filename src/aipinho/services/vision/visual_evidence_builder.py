from __future__ import annotations

from aipinho.schemas.vision.contracts import ImageCitation, ImageSourceRef, VisualEvidence


class VisualEvidenceBuilder:
    def build(self, *, source_ref: ImageSourceRef | None, citation: ImageCitation | None, summary: str, evidence_type: str = "visual_summary", confidence: float = 0.82) -> VisualEvidence:
        blocked: list[str] = []
        if source_ref is None:
            blocked.append("missing_source_ref")
        if citation is None:
            blocked.append("missing_image_citation")
        if blocked:
            raise ValueError(",".join(blocked))
        return VisualEvidence(evidence_type=evidence_type, summary=summary, source_ref=source_ref, citation=citation, confidence=confidence, raw_blob_included=False)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "visual_evidence_builder", "raw_blob_allowed": False}
