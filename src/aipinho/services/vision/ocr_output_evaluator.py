from __future__ import annotations

from aipinho.schemas.vision.contracts import OCRResult
from aipinho.services.vision.image_sensitivity_scanner import ImageSensitivityScanner


class OCROutputEvaluator:
    def __init__(self, sensitivity: ImageSensitivityScanner | None = None) -> None:
        self.sensitivity = sensitivity or ImageSensitivityScanner()

    def evaluate(self, result: OCRResult) -> dict[str, object]:
        violations: list[str] = []
        warnings: list[str] = []
        for block in result.text_blocks:
            if block.confidence is None:
                warnings.append("ocr_block_missing_confidence")
            if block.citation is None:
                violations.append("ocr_block_missing_citation")
            if self.sensitivity.scan_text(block.text)["status"] == "blocked":
                violations.append("secret_ocr_text_blocked")
        return {"status": "accepted" if not violations and not warnings else ("accepted_with_warnings" if not violations else "rejected"), "violations": list(dict.fromkeys(violations)), "warnings": list(dict.fromkeys(warnings))}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "ocr_output_evaluator"}
