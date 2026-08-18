from __future__ import annotations

from aipinho.schemas.vision.contracts import DocumentPageRef, ImageRegion, ImageSourceRef, OCRCitation
from aipinho.services.vision.image_sensitivity_scanner import ImageSensitivityScanner


class OCRCitationBuilder:
    def __init__(self, sensitivity: ImageSensitivityScanner | None = None) -> None:
        self.sensitivity = sensitivity or ImageSensitivityScanner()

    def build(self, source_ref: ImageSourceRef | None, *, excerpt: str, confidence: float, page_ref: DocumentPageRef | None = None, region: ImageRegion | None = None) -> OCRCitation:
        if source_ref is None:
            raise ValueError("missing_source_ref")
        if self.sensitivity.scan_text(excerpt)["status"] == "blocked":
            raise ValueError("secret_excerpt_blocked")
        return OCRCitation(source_ref=source_ref, page_ref=page_ref, region=region, excerpt=excerpt[:800], confidence=confidence)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "ocr_citation_builder", "confidence_required": True}
