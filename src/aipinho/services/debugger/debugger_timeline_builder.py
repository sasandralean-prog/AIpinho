from __future__ import annotations

from aipinho.schemas.debugger.contracts import DebuggerBlockedReason, DebuggerTimeline
from aipinho.services.debugger.debugger_trace_service_v2 import DebuggerTraceServiceV2


class DebuggerTimelineBuilder:
    def __init__(self, traces: DebuggerTraceServiceV2 | None = None) -> None:
        self.traces = traces or DebuggerTraceServiceV2()

    def build(self, trace_id: str) -> DebuggerTimeline:
        trace = self.traces.get(trace_id)
        events = sorted(trace.events, key=lambda item: item.timestamp or "")
        blocked = list(trace.blocked_reasons)
        if any(not event.sanitized for event in events):
            blocked.append(DebuggerBlockedReason(code="unsanitized_event", message="Timeline contains unsanitized event"))
        return DebuggerTimeline(trace_id=trace_id, status="ok" if trace.status == "ok" and not blocked else trace.status, events=events, warnings=trace.warnings, blocked_reasons=blocked, sanitized=True)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "debugger_timeline_builder", "read_only": True}
