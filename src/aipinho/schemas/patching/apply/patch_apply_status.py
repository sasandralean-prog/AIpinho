from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyStatus(AIpinhoModel):
    status: str = "ok"
    patch_apply_enabled: bool = True
    mode: str = "approved_controlled_code_mutation"
    quality_gate_required: bool = True
    approval_required: bool = True
    operator_confirmation_required: bool = True
    backup_required: bool = True
    post_apply_validation_required: bool = True
    direct_diff_apply: bool = False
    payload_patch_apply: bool = False
    shell_enabled: bool = False
    git_enabled: bool = False
    test_execution_enabled: bool = False
    chat_auto_apply: bool = False
    warnings: list[str] = Field(default_factory=list)
