from __future__ import annotations

from typing import Any

from aipinho.schemas.rag.integration.contracts import ContextUsageTrace


class ContextUsageTraceService:
    def item(self, stage: str, status: str, reason: str, data: dict[str, Any] | None = None) -> ContextUsageTrace:
        return ContextUsageTrace(stage=stage, status=status, reason=reason, data=data or {})

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_usage_trace", "raw_context": False}
