from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class HunkApplyResult(AIpinhoModel):
    hunk_id: str
    file_path: str
    status: str
    applied: bool = False
    reason: str = ""
    before_hash: str | None = None
    after_hash: str | None = None
    warnings: list[str] = Field(default_factory=list)
