from __future__ import annotations

from aipinho.schemas.debugger.contracts import DebuggerSourceRef


class DebuggerSourceResolver:
    def resolve(self, payload: dict[str, object], *, source_type: str = "runtime") -> DebuggerSourceRef:
        return DebuggerSourceRef(source_type=source_type, source_id=str(payload.get("run_id") or payload.get("query_id") or payload.get("id") or "unknown"), ref=str(payload.get("ref") or payload.get("path") or ""), citation_id=str(payload.get("citation_id") or "") or None, trace_id=str(payload.get("trace_id") or "") or None)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "debugger_source_resolver"}
