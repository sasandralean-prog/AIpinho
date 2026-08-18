from __future__ import annotations

from aipinho.services.debugger.debug_trace_service import DebugTraceService


class ModelDecisionTraceService:
    def __init__(self, trace_service: DebugTraceService | None = None) -> None:
        self.trace_service = trace_service or DebugTraceService()

    def record_decision(self, *, model_id: str | None, decision: str, reason: str, data: dict[str, object] | None = None) -> str:
        trace_id = self.trace_service.create_trace(category="model_decision", summary="model decision trace")
        self.trace_service.append_event(
            trace_id,
            event_type="model_decision",
            status=decision,
            summary=reason,
            category="model_decision",
            model_id=model_id,
            data=data or {},
        )
        return trace_id
