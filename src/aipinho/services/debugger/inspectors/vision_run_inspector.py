from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding
from aipinho.services.vision.vision_analysis_service import VisionAnalysisService


class VisionRunInspector(BaseInspector):
    target_type = "vision_run"

    def inspect(self, run_id: str):
        run = VisionAnalysisService().get_run(run_id)
        if run is None:
            return self.missing(run_id)
        findings = []
        if not run.get("trace_id"):
            findings.append(finding("vision_run_without_trace", "Vision run has no trace_id"))
        if not run.get("citations"):
            findings.append(finding("vision_run_without_citation", "Vision run has no image citation"))
        if not run.get("evidence"):
            findings.append(finding("vision_run_without_evidence", "Vision run has no visual evidence"))
        return self.result(run_id, {"run": run}, findings, summary="Vision run inspected")
