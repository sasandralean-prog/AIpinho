from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalReport, EvalResult


class EvalReportService:
    def build(self, results: list[EvalResult]) -> EvalReport:
        status = "passed" if all(item.status == "passed" for item in results) else "passed_with_warnings"
        if any(item.status in {"failed", "blocked"} for item in results):
            status = "failed"
        return EvalReport(status=status, results=results, summary=f"{len(results)} evaluation results")
