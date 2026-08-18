from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class EffectiveRolePolicy(AIpinhoModel):
    role_id: str
    allowed: bool = False
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    can_call_model: bool = False
    can_call_tools: bool = False
    can_write: bool = False
    can_patch: bool = False
    can_approve: bool = False
    model_policy: str = "deterministic_only"
    output_contract: str = "plain_text"
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, object]] = Field(default_factory=list)
