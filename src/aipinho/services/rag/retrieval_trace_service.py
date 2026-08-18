from __future__ import annotations

from typing import Any

from aipinho.schemas.rag.retrieval_request import RetrievalTrace


class RetrievalTraceService:
    def item(self, stage: str, status: str, reason: str, *, source_id: str | None = None, data: dict[str, Any] | None = None) -> RetrievalTrace:
        return RetrievalTrace(stage=stage, status=status, reason=reason, source_id=source_id, data=data or {})

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_trace", "sanitized": True}
