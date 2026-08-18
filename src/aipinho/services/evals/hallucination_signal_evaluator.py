from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class HallucinationSignalEvaluator(BaseEvaluator):
    evaluator = "hallucination_signals"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        signals = []
        checks = {
            "patch_applied_without_result": payload.get("claims_patch_applied") and not payload.get("patch_apply_result"),
            "tests_run_without_result": payload.get("claims_tests_run") and not payload.get("test_result"),
            "memory_saved_without_result": payload.get("claims_memory_saved") and not payload.get("memory_result"),
            "rag_used_without_trace": payload.get("claims_rag_used") and not payload.get("rag_trace_id"),
            "vision_ocr_used_without_trace": payload.get("claims_vision_ocr_used") and not payload.get("vision_ocr_trace_id"),
            "auto_selected_14b": payload.get("model_id", "").lower().find("14b") >= 0 and not payload.get("manual_escalation_used"),
        }
        for code, active in checks.items():
            if active:
                signals.append(finding(code, code.replace("_", " ")))
        return self.make_result(request, signals, {"signals": [item.code for item in signals]})
