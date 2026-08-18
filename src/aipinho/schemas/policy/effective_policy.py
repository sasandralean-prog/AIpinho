from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class EffectivePolicy(AIpinhoModel):
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)
    granted_capabilities: list[str] = Field(default_factory=list)
    denied_capabilities: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reasons: dict[str, str] = Field(default_factory=dict)