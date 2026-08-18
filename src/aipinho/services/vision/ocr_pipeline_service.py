from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.vision.contracts import OCRRequest, OCRResult, OCRTextBlock, VisionAudit
from aipinho.services.vision.image_input_validator import ImageInputValidator
from aipinho.services.vision.image_sensitivity_scanner import ImageSensitivityScanner
from aipinho.services.vision.ocr_citation_builder import OCRCitationBuilder
from aipinho.services.vision.ocr_confidence_service import OCRConfidenceService
from aipinho.services.vision.ocr_model_gate_service import OCRModelGateService
from aipinho.services.vision.ocr_output_evaluator import OCROutputEvaluator
from aipinho.services.vision.vision_audit_service import VisionAuditService
from aipinho.services.vision.vision_trace_service import VisionTraceService


class OCRPipelineService:
    def __init__(self) -> None:
        self.validator = ImageInputValidator()
        self.gate = OCRModelGateService()
        self.confidence = OCRConfidenceService()
        self.citations = OCRCitationBuilder()
        self.evaluator = OCROutputEvaluator()
        self.sensitivity = ImageSensitivityScanner()
        self.trace = VisionTraceService()
        self.audit = VisionAuditService()
        self.run_dir = PATHS.project_root / "data" / "runtime" / "ocr" / "runs"

    def extract(self, request: OCRRequest) -> OCRResult:
        trace_id = self.trace.create("ocr_pipeline_started")
        validation = self.validator.validate(request.image)
        if not validation.allowed:
            return self._blocked(trace_id, validation.blocked_reasons, validation.warnings)
        gate = self.gate.decide(request.requested_model_id)
        if not gate["allowed"]:
            return self._blocked(trace_id, list(gate["blocked_reasons"]), list(gate["warnings"]))
        source_ref = request.image.source_ref if request.image else None
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        text = self._extract_text(request, metadata)
        warnings = list(gate["warnings"])
        if not text.strip():
            text = "No readable text was extracted from the provided visual source."
            warnings.append("no_ocr_text_extracted")
        sensitivity = self.sensitivity.scan_text(text)
        if sensitivity["status"] == "blocked":
            return self._blocked(trace_id, ["secret_ocr_text_blocked"], warnings)
        confidence = self.confidence.normalize(self._confidence_value(metadata))
        if confidence.warning:
            warnings.append(confidence.warning)
        citation = self.citations.build(source_ref, excerpt=text, confidence=confidence.value)
        block = OCRTextBlock(text=text, confidence=confidence.value, page=source_ref.page if source_ref else None, citation=citation)
        result = OCRResult(
            status="completed" if confidence.status == "ok" else "degraded",
            model_id=str(gate["model_id"]),
            provider_id=str(gate["provider_id"]),
            text_blocks=[block],
            citations=[citation],
            summary=f"OCR extracted {len(text)} characters with cited confidence.",
            trace_id=trace_id,
            warnings=list(dict.fromkeys(warnings)),
        )
        result.evaluation = self.evaluator.evaluate(result)
        if result.evaluation["status"] == "rejected":
            result.status = "rejected"
            result.blocked_reasons.extend(result.evaluation.get("violations", []))
        self.trace.record(trace_id, event_type="ocr_pipeline", status=result.status, summary=result.summary, data={"model_id": result.model_id, "blocks": len(result.text_blocks)})
        self.audit.record(VisionAudit(event_type="ocr_pipeline", status=result.status, run_id=result.run_id, source_id=source_ref.image_id if source_ref else None, model_id=result.model_id, data={"citations": [item.citation_id for item in result.citations]}))
        self._save(result)
        return result

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        path = self.run_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _extract_text(self, request: OCRRequest, metadata: dict[str, Any]) -> str:
        for key in ("mock_text", "ocr_text", "text"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return request.prompt.strip()

    def _confidence_value(self, metadata: dict[str, Any]) -> float | None:
        value = metadata.get("confidence")
        if value is None:
            return None
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return None

    def _blocked(self, trace_id: str, reasons: list[str], warnings: list[str]) -> OCRResult:
        result = OCRResult(status="blocked", trace_id=trace_id, warnings=warnings, blocked_reasons=list(dict.fromkeys(reasons)))
        self.trace.record(trace_id, event_type="ocr_pipeline", status="blocked", summary="OCR pipeline blocked", data={"blocked_reasons": result.blocked_reasons})
        self._save(result)
        return result

    def _save(self, result: OCRResult) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / f"{result.run_id}.json").write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "ocr_pipeline", "raw_output_hidden": True, "confidence_required": True}
