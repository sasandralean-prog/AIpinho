from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding
from aipinho.services.vision.ocr_pipeline_service import OCRPipelineService


class OCRRunInspector(BaseInspector):
    target_type = "ocr_run"

    def inspect(self, run_id: str):
        run = OCRPipelineService().get_run(run_id)
        if run is None:
            return self.missing(run_id)
        findings = []
        if not run.get("trace_id"):
            findings.append(finding("ocr_run_without_trace", "OCR run has no trace_id"))
        blocks = run.get("text_blocks", []) if isinstance(run.get("text_blocks", []), list) else []
        for block in blocks:
            if isinstance(block, dict) and block.get("confidence") is None:
                findings.append(finding("ocr_without_confidence", "OCR block has no confidence", "high"))
            if isinstance(block, dict) and not block.get("citation"):
                findings.append(finding("ocr_without_citation", "OCR block has no citation"))
        return self.result(run_id, {"run": run}, findings, summary="OCR run inspected")
