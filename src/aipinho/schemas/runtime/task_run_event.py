from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class TaskRunEvent(AIpinhoModel):
    event_id: str
    run_id: str
    sequence: int
    type: str
    status: str
    message: str
    step_id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)
