from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class FallbackAnalysisService(BaseEvaluator):
    evaluator = "fallback_analysis"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        findings = []
        if payload.get("fallback_used") and not payload.get("fallback_reason"):
            findings.append(finding("fallback_reason_missing", "Fallback used without reason", "high"))
        if str(payload.get("fallback_model_id") or "").lower().find("14b") >= 0:
            findings.append(finding("fallback_to_14b_critical", "Fallback to 14B is not allowed automatically"))
        return self.make_result(request, findings, {"fallback_used": bool(payload.get("fallback_used"))})
