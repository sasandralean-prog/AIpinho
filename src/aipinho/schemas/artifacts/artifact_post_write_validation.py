from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactPostWriteValidation(AIpinhoModel):
    passed: bool = False
    file_exists: bool = False
    is_file: bool = False
    hash_match: bool = False
    size_match: bool = False
    target_match: bool = False
    extension_allowed: bool = False
    temp_cleaned: bool = False
    backup_valid: bool | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
