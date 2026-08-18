from __future__ import annotations

from typing import Any

from aipinho.schemas.reports.report_trace import ReportTraceItem


class ReportTraceService:
    def item(self, stage: str, status: str, reason: str, *, rule_id: str | None = None, source: str | None = None, data: dict[str, Any] | None = None) -> ReportTraceItem:
        return ReportTraceItem(stage=stage, status=status, reason=reason, rule_id=rule_id, source=source, data=data or {})
