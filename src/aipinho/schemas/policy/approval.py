from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ApprovalConfig(AIpinhoModel):
    side_effects_require_approval: bool = True
    actions_requiring_approval: list[str] = Field(default_factory=list)
    preview_allowed_without_approval: list[str] = Field(default_factory=list)
    never_auto_execute: list[str] = Field(default_factory=list)
    unknown_action_requires_approval: bool = True


class ApprovalPolicyConfig(AIpinhoModel):
    schema_version: int
    approval: ApprovalConfig


class ApprovalRequirement(AIpinhoModel):
    action: str
    required: bool
    reason: str