from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class RawViewerResult(AIpinhoModel):
    raw_ref_id: str
    status: str
    sanitized_text: str = ""
    hidden_by_default: bool = True
    line_count: int = 0
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)
