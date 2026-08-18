from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult

ReadOnlyExecutionBundleStatus = Literal["executed_readonly", "blocked", "invalid", "degraded", "mixed"]


class ReadOnlyExecutionBundle(AIpinhoModel):
    status: ReadOnlyExecutionBundleStatus
    results: list[ToolExecutionResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_execution_enabled: bool = True
    write_execution_enabled: bool = False
    shell_execution_enabled: bool = False
    patch_apply_enabled: bool = False
