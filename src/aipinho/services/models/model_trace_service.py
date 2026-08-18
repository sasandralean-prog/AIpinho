from __future__ import annotations

from aipinho.services.debugger.debug_trace_service import DebugTraceService


class ModelTraceService:
    def __init__(self, trace_service: DebugTraceService | None = None) -> None:
        self.trace_service = trace_service or DebugTraceService()

    def create_model_trace(self, *, model_id: str | None = None, summary: str = "model trace started") -> str:
        trace_id = self.trace_service.create_trace(category="model", summary=summary)
        self.trace_service.append_event(trace_id, event_type="model_trace_started", status="ok", summary=summary, category="model", model_id=model_id)
        return trace_id

    def record(self, trace_id: str, *, event_type: str, status: str, summary: str, model_id: str | None = None, data: dict[str, object] | None = None) -> None:
        self.trace_service.append_event(trace_id, event_type=event_type, status=status, summary=summary, category="model", model_id=model_id, data=data or {})

    def get_trace(self, trace_id: str) -> dict[str, object]:
        return self.trace_service.get_trace(trace_id)

    def timeline(self, trace_id: str) -> dict[str, object]:
        return self.trace_service.timeline(trace_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "model_trace"}
