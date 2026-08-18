from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class LatencyCostEvaluator(BaseEvaluator):
    evaluator = "latency_cost"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        findings = []
        model = str(payload.get("model_id") or "")
        first = int(payload.get("first_token_ms", 0) or 0)
        total = int(payload.get("total_ms", 0) or 0)
        if payload.get("timeout"):
            findings.append(finding("model_timeout", "Model run timed out"))
        if "14b" in model.lower() and not payload.get("latency_warning_acknowledged"):
            findings.append(finding("manual_14b_latency_ack_missing", "14B latency requires explicit acknowledgement"))
        if first > int(payload.get("first_token_budget_ms", 30000) or 30000):
            findings.append(finding("first_token_latency_high", "First token latency exceeds budget", "warning"))
        return self.make_result(request, findings, {"first_token_ms": first, "total_ms": total, "model_id": model})
