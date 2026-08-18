from __future__ import annotations

from typing import Any

from aipinho.schemas.analysis.analysis_trace import AnalysisTraceItem


class AnalysisTraceService:
    def item(self, stage: str, status: str, reason: str, *, source: str | None = None, data: dict[str, Any] | None = None) -> AnalysisTraceItem:
        return AnalysisTraceItem(stage=stage, status=status, reason=reason, source=source, data=data or {})

    def from_raw(self, raw_items: list[dict[str, Any]]) -> list[AnalysisTraceItem]:
        items: list[AnalysisTraceItem] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            items.append(
                AnalysisTraceItem(
                    stage=str(raw.get("stage", "unknown")),
                    status=str(raw.get("status", raw.get("decision", "ok"))),
                    reason=str(raw.get("reason", raw.get("rule", ""))),
                    source=raw.get("source"),
                    data={k: v for k, v in raw.items() if k not in {"stage", "status", "decision", "reason", "source"}},
                )
            )
        return items
