from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.tools.tool_trace import ToolTraceItem

ToolResultStatus = Literal["simulated", "blocked", "invalid", "needs_approval", "degraded"]


class ToolDryRunResultItem(AIpinhoModel):
    tool_id: str
    status: ToolResultStatus
    would_do: str
    would_use_actions: list[str] = Field(default_factory=list)
    would_require_capabilities: list[str] = Field(default_factory=list)
    would_require_approval: list[str] = Field(default_factory=list)
    potential_side_effects: list[str] = Field(default_factory=list)
    input_valid: bool = True
    warnings: list[str] = Field(default_factory=list)
    trace: list[ToolTraceItem] = Field(default_factory=list)
