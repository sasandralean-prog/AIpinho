from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactDiffPreview(AIpinhoModel):
    available: bool = False
    target_exists: bool = False
    diff_type: str = "none"
    old_summary: str | None = None
    new_summary: str | None = None
    diff_preview: str | None = None
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)
