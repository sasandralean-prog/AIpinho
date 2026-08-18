from __future__ import annotations

from aipinho.services.debugger.debug_trace_service import DebugTraceService


class DebugTimelineService:
    def __init__(self, trace_service: DebugTraceService | None = None) -> None:
        self.trace_service = trace_service or DebugTraceService()

    def timeline(self, trace_id: str) -> dict[str, object]:
        return self.trace_service.timeline(trace_id)
