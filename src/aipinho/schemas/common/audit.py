from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel


class AuditEvent(AIpinhoModel):
    event_id: str
    created_at: str
    actor: Actor = Field(default_factory=Actor)
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)