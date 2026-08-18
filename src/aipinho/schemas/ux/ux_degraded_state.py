from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXDegradedState(AIpinhoModel):
    service_id: str
    state: str
    severity: str = "warning"
    human_message: str
    allowed_actions: list[str] = Field(default_factory=list)
