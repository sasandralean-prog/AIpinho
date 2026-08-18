from __future__ import annotations

from aipinho.schemas.evaluation.evaluation_result import EvaluationResult


class EvaluationAuditService:
    _events: list[dict[str, object]] = []

    def record(self, result: EvaluationResult) -> dict[str, object]:
        event = {
            "evaluation_id": result.evaluation_id,
            "status": result.status,
            "score": result.score,
            "violations": list(result.violations),
            "warnings": list(result.warnings),
        }
        self._events.append(event)
        return event

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "evaluation_audit", "events": len(self._events), "persistent_write": False}
