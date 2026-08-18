from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding


class OutputEvaluationInspector(BaseInspector):
    target_type = "output_evaluation"

    def inspect_payload(self, evaluation_id: str, payload: dict):
        findings = []
        status = str(payload.get("status") or "")
        if status in {"rejected", "needs_retry", "degraded"}:
            findings.append(finding("output_evaluation_not_accepted", f"Evaluation status is {status}"))
        if not payload:
            findings.append(finding("output_evaluation_missing", "Output evaluation payload is missing"))
        return self.result(evaluation_id, {"evaluation": payload}, findings, summary="Output evaluation inspected")

    def inspect(self, evaluation_id: str):
        return self.missing(evaluation_id)
