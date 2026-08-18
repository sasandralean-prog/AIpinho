from __future__ import annotations
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class SideEffectValidation(AIpinhoModel):
    status: str
    side_effects_detected: bool = False
    violations: list[str] = Field(default_factory=list)
    allowed_internal_writes: list[str] = Field(default_factory=list)
