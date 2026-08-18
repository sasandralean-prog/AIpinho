from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class DebugTraceRef(AIpinhoModel):
    trace_id: str
    trace_path: str | None = None
    timeline_path: str | None = None
