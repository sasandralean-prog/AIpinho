from __future__ import annotations

from typing import Any

from aipinho.schemas.debugger.contracts import DebuggerFinding, DebuggerInspectionResult, DebuggerTimeline, DebuggerTimelineEvent
from aipinho.services.debugger.debugger_sanitizer import DebuggerSanitizer


def to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def finding(code: str, message: str, severity: str = "critical") -> DebuggerFinding:
    return DebuggerFinding(code=code, message=message, severity=severity)  # type: ignore[arg-type]


class BaseInspector:
    target_type = "unknown"

    def __init__(self) -> None:
        self.sanitizer = DebuggerSanitizer()

    def missing(self, target_id: str) -> DebuggerInspectionResult:
        return DebuggerInspectionResult(target_type=self.target_type, target_id=target_id, status="missing", summary=f"{self.target_type} not found", findings=[finding(f"{self.target_type}_not_found", "Requested target was not found")])

    def result(self, target_id: str, data: dict[str, Any], findings: list[DebuggerFinding] | None = None, summary: str = "") -> DebuggerInspectionResult:
        findings = findings or []
        status = "degraded" if any(item.severity in {"high", "critical"} for item in findings) else "ok"
        event = DebuggerTimelineEvent(event_type=f"{self.target_type}_inspection", category="debugger_inspector", status=status, summary=summary or f"{self.target_type} inspected", data={"target_id": target_id})
        return DebuggerInspectionResult(target_type=self.target_type, target_id=target_id, status=status, summary=summary or f"{self.target_type} inspected", data=self.sanitizer.sanitize(data), findings=findings, timeline=DebuggerTimeline(status=status, events=[event]), sanitized=True, read_only=True)
