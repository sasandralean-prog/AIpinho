from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.diff_preview import DiffPreview


class DiffProposal(AIpinhoModel):
    proposal_id: str
    plan_id: str
    status: str = "not_generated"
    diff: DiffPreview = Field(default_factory=DiffPreview)
    apply_enabled: bool = False
    write_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
