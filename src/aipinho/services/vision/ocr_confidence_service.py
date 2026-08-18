from __future__ import annotations

from aipinho.schemas.vision.contracts import OCRConfidence
from aipinho.services.vision.config import vision_config


class OCRConfidenceService:
    def __init__(self) -> None:
        self.config = vision_config("ocr_confidence_policy.yaml")

    def normalize(self, value: float | None) -> OCRConfidence:
        policy = self.config.get("confidence", {}) if isinstance(self.config.get("confidence", {}), dict) else {}
        if value is None:
            return OCRConfidence(value=0.0, status=str(policy.get("missing_confidence_status", "degraded")), warning="missing_confidence")
        minimum = float(policy.get("minimum_acceptable", 0.55) or 0.55)
        return OCRConfidence(value=value, status="ok" if value >= minimum else "degraded", warning=None if value >= minimum else "confidence_below_minimum")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "ocr_confidence", "confidence_required": True}
