from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyApproval(AIpinhoModel):
    approval_id: str
    plan_id: str
    quality_id: str
    status: str
    diff_hash: str
    target_files: list[str] = Field(default_factory=list)
