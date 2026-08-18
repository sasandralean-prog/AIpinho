from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchValidationResult(AIpinhoModel):
    valid: bool = False
    status: str = "invalid"
    no_apply: bool = True
    no_write: bool = True
    evidence_valid: bool = False
    diff_valid: bool = False
    risk_valid: bool = False
    rollback_valid: bool = False
    tests_recommended: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
