from __future__ import annotations
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class ValidationGateDecision(AIpinhoModel):
    status: str
    score: float
    safe_to_display: bool = True
    warnings: list[str] = Field(default_factory=list)
    blocking_findings: list[str] = Field(default_factory=list)
