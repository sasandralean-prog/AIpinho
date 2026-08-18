from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RollbackNote(AIpinhoModel):
    file_path: str
    original_hash: str | None = None
    summary: str = ""
    automatic_rollback_enabled: bool = False
    steps: list[str] = Field(default_factory=list)
