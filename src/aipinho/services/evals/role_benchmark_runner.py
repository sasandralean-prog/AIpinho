from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class RoleBenchmarkRunner(BaseEvaluator):
    evaluator = "role"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        findings = []
        if not payload.get("role_id"):
            findings.append(finding("role_id_missing", "Role evaluation requires role_id", "high"))
        if not payload.get("output_contract"):
            findings.append(finding("role_output_contract_missing", "Role output contract missing"))
        return self.make_result(request, findings, {})
