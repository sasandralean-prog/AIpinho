from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RolePipelineTraceItem(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: f"role_trace_{uuid4().hex}")
    stage: str
    status: str
    reason: str = ""
    role_id: str | None = None
    pass_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
