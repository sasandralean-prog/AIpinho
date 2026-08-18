from __future__ import annotations

from aipinho.schemas.vision.contracts import VisionAnalysisResult


class VisionOutputEvaluator:
    def evaluate(self, result: VisionAnalysisResult) -> dict[str, object]:
        violations: list[str] = []
        warnings: list[str] = []
        if not result.citations:
            violations.append("visual_output_missing_citation")
        if not result.evidence:
            violations.append("visual_output_missing_evidence")
        if any(item.raw_blob_included for item in result.evidence):
            violations.append("raw_blob_in_output")
        if not result.findings:
            warnings.append("no_visual_findings")
        return {"status": "accepted" if not violations and not warnings else ("accepted_with_warnings" if not violations else "rejected"), "violations": violations, "warnings": warnings}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vision_output_evaluator"}
