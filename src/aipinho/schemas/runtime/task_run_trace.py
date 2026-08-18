from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class TaskRunTraceItem(AIpinhoModel):
    stage: str
    status: str
    reason: str = ""
    step_id: str | None = None
    source: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = Field(default_factory=dict)
