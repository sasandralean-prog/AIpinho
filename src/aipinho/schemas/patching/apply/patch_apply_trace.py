from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyTrace(AIpinhoModel):
    apply_run_id: str
    events: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
