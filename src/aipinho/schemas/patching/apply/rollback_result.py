from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RollbackResult(AIpinhoModel):
    status: str = "not_requested"
    completed: bool = False
    restored_files: list[str] = Field(default_factory=list)
    failed_files: list[str] = Field(default_factory=list)
    manual_review_required: bool = False
    warnings: list[str] = Field(default_factory=list)
