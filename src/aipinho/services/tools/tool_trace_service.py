from __future__ import annotations

from typing import Any

from aipinho.schemas.tools.tool_trace import ToolTraceItem


class ToolTraceService:
    def item(
        self,
        *,
        stage: str,
        rule: str,
        decision: str,
        reason: str,
        severity: str = "info",
        source: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> ToolTraceItem:
        return ToolTraceItem(
            stage=stage,
            rule=rule,
            decision=decision,
            reason=reason,
            severity=severity,  # type: ignore[arg-type]
            source=source,
            data=data or {},
        )
