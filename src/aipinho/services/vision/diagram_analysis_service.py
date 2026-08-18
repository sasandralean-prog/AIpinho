from __future__ import annotations

from aipinho.schemas.vision.contracts import DiagramAnalysisResult, VisionAnalysisRequest
from aipinho.services.vision.vision_analysis_service import VisionAnalysisService


class DiagramAnalysisService:
    def __init__(self) -> None:
        self.analysis = VisionAnalysisService()

    def analyze(self, request: VisionAnalysisRequest) -> DiagramAnalysisResult:
        result = self.analysis.analyze(request.model_copy(update={"purpose": "diagram_analysis"}))
        return DiagramAnalysisResult(**result.model_dump(), diagram_elements=[{"kind": "diagram_observation", "summary": result.summary, "confidence": 0.84}] if result.citations else [])

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "diagram_analysis"}
