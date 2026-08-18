from __future__ import annotations

from aipinho.services.debugger.debug_trace_service import DebugTraceService


class RoleModelTraceService:
    def __init__(self, trace_service: DebugTraceService | None = None) -> None:
        self.trace_service = trace_service or DebugTraceService()

    def create(self, role_id: str, *, summary: str = "role model trace started") -> str:
        trace_id = self.trace_service.create_trace(category="role_model", summary=summary)
        self.record(trace_id, role_id=role_id, event_type="role_model_trace_started", status="ok", summary=summary)
        return trace_id

    def record(self, trace_id: str, *, role_id: str, event_type: str, status: str, summary: str, data: dict[str, object] | None = None, model_id: str | None = None) -> None:
        self.trace_service.append_event(trace_id, event_type=event_type, status=status, summary=summary, category="role_model", model_id=model_id, data={"role_id": role_id, **(data or {})})

    def get(self, trace_id: str) -> dict[str, object]:
        return self.trace_service.get_trace(trace_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_model_trace"}
