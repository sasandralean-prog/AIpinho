from __future__ import annotations

from aipinho.schemas.vision.contracts import UIInspectionRequest, UIInspectionResult
from aipinho.services.vision.vision_analysis_service import VisionAnalysisService


class UIInspectionService:
    def __init__(self) -> None:
        self.analysis = VisionAnalysisService()

    def inspect(self, request: UIInspectionRequest) -> UIInspectionResult:
        result = self.analysis.analyze(request)
        return UIInspectionResult(**result.model_dump(), ui_elements=[{"kind": "screen_region", "summary": result.summary, "citation_id": result.citations[0].citation_id if result.citations else None}] if result.citations else [])

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "ui_inspection"}
