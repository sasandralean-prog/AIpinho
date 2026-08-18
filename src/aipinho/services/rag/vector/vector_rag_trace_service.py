from __future__ import annotations

from aipinho.services.debugger.debug_trace_service import DebugTraceService


class VectorRAGTraceService:
    def __init__(self, traces: DebugTraceService | None = None) -> None:
        self.traces = traces or DebugTraceService()

    def create(self, summary: str) -> str:
        return self.traces.create_trace(category="vector_rag", summary=summary)

    def record(self, trace_id: str, *, event_type: str, status: str, summary: str, data: dict[str, object] | None = None) -> None:
        self.traces.append_event(trace_id, event_type=event_type, status=status, summary=summary, category="vector_rag", data=data or {})

    def get(self, trace_id: str) -> dict[str, object]:
        return self.traces.get_trace(trace_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vector_rag_trace"}
