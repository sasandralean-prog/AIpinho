from __future__ import annotations

from typing import Any

from aipinho.schemas.evals.contracts import EvalFinding, EvalRequest, EvalResult, EvalRun, EvalTrace
from aipinho.services.evals.eval_run_store import EvalRunStore
from aipinho.services.evals.eval_sanitizer import EvalSanitizer


def finding(code: str, message: str, severity: str = "critical") -> EvalFinding:
    return EvalFinding(code=code, message=message, severity=severity)  # type: ignore[arg-type]


class BaseEvaluator:
    evaluator = "base"

    def __init__(self, store: EvalRunStore | None = None) -> None:
        self.store = store or EvalRunStore()
        self.sanitizer = EvalSanitizer()

    def make_result(self, request: EvalRequest, findings: list[EvalFinding], metrics: dict[str, Any] | None = None) -> EvalResult:
        critical = any(item.severity == "critical" for item in findings)
        high = any(item.severity == "high" for item in findings)
        warning = any(item.severity == "warning" for item in findings)
        status = "failed" if critical else ("degraded" if high else ("passed_with_warnings" if warning else "passed"))
        score = 0.0 if critical else (0.5 if high else (0.8 if warning else 1.0))
        result = EvalResult(status=status, score=score, evaluator=self.evaluator, findings=findings, metrics=self.sanitizer.sanitize(metrics or {}), trace=EvalTrace(events=[{"event_type": self.evaluator, "status": status, "findings": len(findings)}]) if request.include_trace else None)
        self.store.save(EvalRun(request=request, result=result))
        return result

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": self.evaluator, "read_only": True}
