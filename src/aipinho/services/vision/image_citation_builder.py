from __future__ import annotations

from aipinho.schemas.vision.contracts import ImageCitation, ImageRegion, ImageSourceRef


class ImageCitationBuilder:
    def build(self, source_ref: ImageSourceRef | None, *, summary: str, confidence: float = 0.82, region: ImageRegion | None = None) -> ImageCitation:
        if source_ref is None:
            raise ValueError("missing_source_ref")
        return ImageCitation(image_id=source_ref.image_id, source_ref=source_ref, region=region, summary=summary[:800], confidence=confidence)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "image_citation_builder", "source_ref_required": True}
