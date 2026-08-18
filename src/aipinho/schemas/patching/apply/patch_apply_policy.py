from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyPolicy(AIpinhoModel):
    enabled: bool = True
    mode: str = "approved_controlled_code_mutation"
    require_quality_gate: bool = True
    require_explicit_approval: bool = True
    require_operator_confirmation: bool = True
    allowed_quality_statuses: list[str] = Field(default_factory=lambda: ["passed"])
    allow_chat_auto_apply: bool = False
    allow_direct_diff_apply: bool = False
    allow_payload_patch_apply: bool = False
