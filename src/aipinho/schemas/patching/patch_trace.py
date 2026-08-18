from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchTrace(AIpinhoModel):
    plan_id: str
    items: list[str] = Field(default_factory=list)
