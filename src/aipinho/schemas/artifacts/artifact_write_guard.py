from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWriteGuard(AIpinhoModel):
    allowed: bool = False
    status: str = "blocked"
    preview_id: str | None = None
    approval_id: str | None = None
    target_path: str | None = None
    content_hash: str = ""
    resolved_content: str = ""
    would_overwrite: bool = False
    existing_hash: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
