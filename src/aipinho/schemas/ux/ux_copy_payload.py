from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXCopyPayload(AIpinhoModel):
    copy_id: str
    allowed: bool
    text: str = ""
    blocked_reasons: list[str] = Field(default_factory=list)
