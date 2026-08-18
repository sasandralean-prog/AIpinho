from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchPlanningStatus(AIpinhoModel):
    status: str = "ok"
    enabled: bool = True
    mode: str = "proposal_only"
    apply_enabled: bool = False
    write_enabled: bool = False
    shell_enabled: bool = False
    git_write_enabled: bool = False
    test_execution_enabled: bool = False
    real_model_auto_use: bool = False
    allowed_extensions: list[str] = Field(default_factory=list)
    blocked_extensions: list[str] = Field(default_factory=list)
    max_files_per_plan: int = 5
    max_total_hunks: int = 20
    warnings: list[str] = Field(default_factory=list)
