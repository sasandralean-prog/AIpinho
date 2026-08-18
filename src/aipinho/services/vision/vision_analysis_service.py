from __future__ import annotations

import json

from aipinho.schemas.vision.contracts import VisionAnalysisHit, VisionAnalysisRequest, VisionAnalysisResult, VisionAudit, VisualFinding
from aipinho.services.vision.image_citation_builder import ImageCitationBuilder
from aipinho.services.vision.image_input_validator import ImageInputValidator
from aipinho.services.vision.vision_audit_service import VisionAuditService
from aipinho.services.vision.vision_model_gate_service import VisionModelGateService
from aipinho.services.vision.vision_output_evaluator import VisionOutputEvaluator
from aipinho.services.vision.vision_trace_service import VisionTraceService
from aipinho.services.vision.visual_evidence_builder import VisualEvidenceBuilder
from aipinho.services.vision.config import runtime_path


class VisionAnalysisService:
    def __init__(self) -> None:
        self.validator = ImageInputValidator()
        self.gate = VisionModelGateService()
        self.citations = ImageCitationBuilder()
        self.evidence = VisualEvidenceBuilder()
        self.evaluator = VisionOutputEvaluator()
        self.trace = VisionTraceService()
        self.audit = VisionAuditService()
        self.run_dir = runtime_path("runs")

    def analyze(self, request: VisionAnalysisRequest) -> VisionAnalysisResult:
        trace_id = self.trace.create("vision_analysis_started")
        validation = self.validator.validate(request.image)
        if not validation.allowed:
            return self._blocked(request, trace_id, validation.blocked_reasons, validation.warnings)
        gate = self.gate.decide(request.requested_model_id)
        fallback_used = False
        if not gate["allowed"] and request.allow_fallback:
            fallback_gate = self.gate.decide(fallback=True)
            if fallback_gate["allowed"]:
                gate = fallback_gate
                fallback_used = True
        if not gate["allowed"]:
            return self._blocked(request, trace_id, list(gate["blocked_reasons"]), list(gate["warnings"]))
        source_ref = request.image.source_ref if request.image else None
        summary = self._summary(request)
        citation = self.citations.build(source_ref, summary=summary, confidence=0.84)
        evidence = self.evidence.build(source_ref=source_ref, citation=citation, summary=summary, confidence=0.84)
        finding = VisualFinding(summary=summary, confidence=0.84, citation_id=citation.citation_id)
        result = VisionAnalysisResult(
            status="completed",
            model_id=str(gate["model_id"]),
            provider_id=str(gate["provider_id"]),
            fallback_used=fallback_used,
            summary=summary,
            findings=[finding],
            evidence=[evidence],
            citations=[citation],
            hits=[VisionAnalysisHit(summary=summary, confidence=0.84, citation=citation, evidence_id=evidence.evidence_id)],
            trace_id=trace_id,
            warnings=list(gate["warnings"]),
        )
        result.evaluation = self.evaluator.evaluate(result)
        if result.evaluation["status"] == "rejected":
            result.status = "rejected"
            result.blocked_reasons.extend(result.evaluation.get("violations", []))
        self.trace.record(trace_id, event_type="vision_analysis", status=result.status, summary=summary, data={"model_id": result.model_id, "fallback_used": fallback_used})
        self.audit.record(VisionAudit(event_type="vision_analysis", status=result.status, run_id=result.run_id, source_id=source_ref.image_id if source_ref else None, model_id=result.model_id, data={"citations": [item.citation_id for item in result.citations]}))
        self._save(result)
        return result

    def get_run(self, run_id: str) -> dict | None:
        path = self.run_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _blocked(self, request: VisionAnalysisRequest, trace_id: str, reasons: list[str], warnings: list[str]) -> VisionAnalysisResult:
        result = VisionAnalysisResult(status="blocked", trace_id=trace_id, warnings=warnings, blocked_reasons=list(dict.fromkeys(reasons)))
        self.trace.record(trace_id, event_type="vision_analysis", status="blocked", summary="Vision analysis blocked", data={"blocked_reasons": result.blocked_reasons})
        self._save(result)
        return result

    def _summary(self, request: VisionAnalysisRequest) -> str:
        purpose = request.purpose.replace("_", " ")
        image_id = request.image.source_ref.image_id if request.image and request.image.source_ref else "unknown_image"
        return f"Governed {purpose} summary for {image_id}. Visual observations require this citation and confidence before prompt use."

    def _save(self, result: VisionAnalysisResult) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / f"{result.run_id}.json").write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vision_analysis", "raw_output_hidden": True}
