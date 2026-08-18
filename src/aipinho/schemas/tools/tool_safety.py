from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.tools.tool_trace import ToolTraceItem

ToolInputValidationStatus = Literal["valid", "invalid"]
ToolSafetyStatus = Literal["allowed", "blocked", "needs_approval", "invalid", "degraded"]


class ToolInputValidationResult(AIpinhoModel):
    status: ToolInputValidationStatus
    input_valid: bool = False
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[ToolTraceItem] = Field(default_factory=list)


class ToolSafetyDecision(AIpinhoModel):
    status: ToolSafetyStatus
    blocked: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safe_to_execute: bool = False
    safe_to_dry_run: bool = False
    trace: list[ToolTraceItem] = Field(default_factory=list)
