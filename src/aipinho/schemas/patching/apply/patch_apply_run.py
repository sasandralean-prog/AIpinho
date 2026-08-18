from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.apply.patch_apply_guard import PatchApplyGuardResult


class PatchApplyRun(AIpinhoModel):
    apply_run_id: str
    plan_id: str
    quality_id: str
    approval_id: str
    status: str = "created"
    workspace: str
    operator_confirmed: bool = False
    diff_hash: str
    target_files: list[str] = Field(default_factory=list)
    original_hashes: dict[str, str] = Field(default_factory=dict)
    backup_ids: list[str] = Field(default_factory=list)
    guard: PatchApplyGuardResult = Field(default_factory=PatchApplyGuardResult)
    result_id: str | None = None
    created_at: str
    updated_at: str
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
