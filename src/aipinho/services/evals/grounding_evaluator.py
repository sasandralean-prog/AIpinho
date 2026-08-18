from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class GroundingEvaluator(BaseEvaluator):
    evaluator = "grounding"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        output = str(payload.get("output", ""))
        allowed_refs = set(payload.get("allowed_refs", []) or [])
        findings = []
        for ref in payload.get("referenced_refs", []) or []:
            if ref not in allowed_refs:
                findings.append(finding("unsupported_source_reference", f"Output references source outside context: {ref}", "high"))
        unsupported_claims = [term for term in ["patch applied", "tests passed", "memory saved", "rag used"] if term in output.lower() and term not in set(payload.get("supported_claims", []) or [])]
        for claim in unsupported_claims:
            findings.append(finding("unsupported_execution_claim", f"Unsupported claim: {claim}"))
        return self.make_result(request, findings, {"allowed_refs": len(allowed_refs)})
