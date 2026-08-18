from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalTrace


class EvalTraceService:
    def create(self, event_type: str, status: str, data: dict | None = None) -> EvalTrace:
        return EvalTrace(events=[{"event_type": event_type, "status": status, "data": data or {}}])

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "eval_trace", "read_only": True}
