from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWriteValidation(AIpinhoModel):
    valid: bool = False
    target_revalidated: bool = False
    content_revalidated: bool = False
    risk_revalidated: bool = False
    approval_valid: bool = False
    hash_locked: bool = False
    target_locked: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
