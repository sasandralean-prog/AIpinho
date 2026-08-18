from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXLatencyIndicator(AIpinhoModel):
    target: str
    latency_ms: int | None = None
    state: str = "unknown"
    human_message: str | None = None
