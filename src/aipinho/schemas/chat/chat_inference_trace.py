from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ChatInferenceTraceItem(AIpinhoModel):
    stage: str
    status: str
    reason: str | None = None
    source: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
