from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.apply.patch_apply_file_result import PatchApplyFileResult
from aipinho.schemas.patching.apply.post_apply_validation import PostApplyValidation
from aipinho.schemas.patching.apply.rollback_result import RollbackResult


class PatchApplyResult(AIpinhoModel):
    apply_run_id: str
    plan_id: str
    status: str
    safe_to_report_success: bool = False
    files: list[PatchApplyFileResult] = Field(default_factory=list)
    post_apply_validation: PostApplyValidation = Field(default_factory=PostApplyValidation)
    rollback: RollbackResult = Field(default_factory=RollbackResult)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
