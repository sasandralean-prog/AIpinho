from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXActionState(AIpinhoModel):
    action_id: str
    state: str = "idle"
    blocked: bool = False
    human_message: str | None = None
