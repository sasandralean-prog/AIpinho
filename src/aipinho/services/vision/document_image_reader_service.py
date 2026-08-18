from __future__ import annotations

from aipinho.schemas.vision.contracts import DocumentReadRequest, DocumentReadResult
from aipinho.services.vision.config import vision_config
from aipinho.services.vision.ocr_pipeline_service import OCRPipelineService


class DocumentImageReaderService:
    def __init__(self) -> None:
        self.ocr = OCRPipelineService()
        self.config = vision_config("document_read_policy.yaml")

    def read(self, request: DocumentReadRequest) -> DocumentReadResult:
        result = self.ocr.extract(request)
        page_limit = self._max_pages(request)
        page_count = int((request.image.metadata or {}).get("page_count", 1)) if request.image else 1
        processed = min(max(page_count, 1), page_limit)
        partial = page_count > processed
        doc = DocumentReadResult(**result.model_dump(), pages_processed=processed, partial=partial)
        if partial:
            doc.status = "degraded" if doc.status == "completed" else doc.status
            doc.warnings.append("document_page_limit_applied")
        return doc

    def _max_pages(self, request: DocumentReadRequest) -> int:
        if request.max_pages:
            return max(1, int(request.max_pages))
        limits = self.config.get("limits", {}) if isinstance(self.config.get("limits", {}), dict) else {}
        return int(limits.get("max_pages", 20) or 20)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "document_image_reader", "ocr_required": True, "raw_document_hidden": True}
