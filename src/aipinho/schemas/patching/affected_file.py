from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class AffectedFile(AIpinhoModel):
    path: str
    normalized_path: str | None = None
    relative_path: str | None = None
    status: str = "unknown"
    original_hash: str | None = None
    size_bytes: int = 0
    risk_level: str = "medium"
    evidence_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
