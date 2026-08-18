from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyReconciliation(AIpinhoModel):
    status: str = "unknown"
    expected_targets: list[str] = Field(default_factory=list)
    observed_writes: list[str] = Field(default_factory=list)
    unexpected_writes: list[str] = Field(default_factory=list)
    temp_files: list[str] = Field(default_factory=list)
