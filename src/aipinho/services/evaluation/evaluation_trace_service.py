from __future__ import annotations

from typing import Any

from aipinho.schemas.evaluation.evaluation_trace import EvaluationTraceItem


class EvaluationTraceService:
    def item(self, stage: str, status: str, reason: str | None = None, *, data: dict[str, Any] | None = None, source: str | None = None) -> EvaluationTraceItem:
        return EvaluationTraceItem(stage=stage, status=status, reason=reason, data=data or {}, source=source)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "evaluation_trace"}
