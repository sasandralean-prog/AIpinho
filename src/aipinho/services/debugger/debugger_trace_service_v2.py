from __future__ import annotations

from aipinho.schemas.debugger.contracts import DebuggerBlockedReason, DebuggerTrace, DebuggerTimelineEvent, DebuggerWarning
from aipinho.services.debugger.debugger_sanitizer import DebuggerSanitizer
from aipinho.services.debugger.debugger_trace_store import DebuggerTraceStore


class DebuggerTraceServiceV2:
    def __init__(self, store: DebuggerTraceStore | None = None, sanitizer: DebuggerSanitizer | None = None) -> None:
        self.store = store or DebuggerTraceStore()
        self.sanitizer = sanitizer or DebuggerSanitizer()

    def get(self, trace_id: str) -> DebuggerTrace:
        raw = self.store.get(trace_id)
        if raw is None:
            return DebuggerTrace(trace_id=trace_id, status="missing", blocked_reasons=[DebuggerBlockedReason(code="trace_not_found", message="Trace was not found")])
        clean = self.sanitizer.sanitize(raw)
        events = []
        for item in clean.get("events", []) if isinstance(clean, dict) else []:
            if not isinstance(item, dict):
                continue
            events.append(DebuggerTimelineEvent(trace_id=trace_id, event_id=str(item.get("event_id") or "event"), event_type=str(item.get("event_type") or "unknown"), category=str(item.get("category") or raw.get("category") or "debugger"), status=str(item.get("status") or "ok"), summary=str(item.get("summary") or ""), timestamp=str(item.get("created_at") or item.get("timestamp") or raw.get("created_at") or ""), data=item.get("data", {}) if isinstance(item.get("data", {}), dict) else {}, sanitized=True))
        warnings = [] if events else [DebuggerWarning(code="trace_has_no_events", message="Trace exists but has no events")]
        return DebuggerTrace(trace_id=trace_id, status="ok", category=str(raw.get("category", "debugger")), events=events, warnings=warnings)

    def resolve(self, payload: dict[str, object]) -> dict[str, object]:
        for key in ("trace_id", "run_id", "query_id", "plan_id", "evaluation_id"):
            value = payload.get(key)
            if isinstance(value, str) and value.startswith("trace_"):
                return {"status": "ok", "trace_id": value, "target_type": key}
        return {"status": "missing", "trace_id": None, "blocked_reasons": ["trace_id_not_provided"]}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "debugger_trace_v2", "sanitized": True, "read_only": True}
