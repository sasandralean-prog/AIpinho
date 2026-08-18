from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PostApplyValidation(AIpinhoModel):
    status: str = "unknown"
    passed: bool = False
    validation_id: str | None = None
    final_hashes: dict[str, str] = Field(default_factory=dict)
    checked_files: list[str] = Field(default_factory=list)
    unexpected_writes: list[str] = Field(default_factory=list)
    temp_files_remaining: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
