from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchHunk(AIpinhoModel):
    hunk_id: str
    file_path: str
    original: str
    replacement: str
    reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
