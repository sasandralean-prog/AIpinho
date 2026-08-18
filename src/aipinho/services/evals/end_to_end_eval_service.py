from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class EndToEndEvalService(BaseEvaluator):
    evaluator = "end_to_end"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        required = ["trace", "role", "model", "policy", "output_evaluation"]
        findings = [finding(f"missing_{key}", f"End-to-end payload missing {key}", "high") for key in required if not payload.get(key)]
        return self.make_result(request, findings, {"required_checked": required})
