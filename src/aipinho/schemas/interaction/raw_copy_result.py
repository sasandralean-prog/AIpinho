from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class RawCopyResult(AIpinhoModel):
    raw_ref_id: str
    allowed: bool
    text: str = ""
    blocked_reasons: list[str] = Field(default_factory=list)
