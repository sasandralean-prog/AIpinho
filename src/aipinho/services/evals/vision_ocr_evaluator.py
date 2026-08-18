from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class VisionOCREvaluator(BaseEvaluator):
    evaluator = "vision_ocr"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        findings = []
        if not payload.get("trace_id"):
            findings.append(finding("vision_ocr_trace_missing", "Vision/OCR result requires trace_id", "high"))
        if not payload.get("citations"):
            findings.append(finding("vision_ocr_citation_missing", "Vision/OCR result requires citation"))
        for block in payload.get("text_blocks", []) or []:
            if isinstance(block, dict) and block.get("confidence") is None:
                findings.append(finding("ocr_confidence_missing", "OCR block confidence missing", "high"))
        return self.make_result(request, findings, {})
