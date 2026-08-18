from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class SafetyEnvelope(AIpinhoModel):
    envelope_id: str
    purpose: str
    rules: list[str] = Field(default_factory=list)
    policy_status: str | None = None
    read_only: bool = True
    real_inference: bool = False
    warnings: list[str] = Field(default_factory=list)
