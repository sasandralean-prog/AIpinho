from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchEvidence(AIpinhoModel):
    evidence_id: str
    source_type: str = "user_request"
    source_id: str | None = None
    source_path: str | None = None
    excerpt: str = ""
    line_start: int | None = None
    line_end: int | None = None
    confidence: float = 0.5
    warnings: list[str] = Field(default_factory=list)
