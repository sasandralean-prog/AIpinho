from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.schemas.tools.tool_result import ToolDryRunResultItem, ToolResultStatus
from aipinho.schemas.tools.tool_trace import ToolTraceItem

DryRunSource = Literal["direct", "draft", "preview", "approval", "chat"]


class ToolDryRunPlan(AIpinhoModel):
    dry_run_id: str = Field(default_factory=lambda: f"dry_run_{uuid4().hex}")
    source: DryRunSource = "direct"
    tool_calls: list[ToolCall] = Field(default_factory=list)
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    approval_snapshot: dict[str, Any] = Field(default_factory=dict)
    workspace_status: dict[str, Any] = Field(default_factory=dict)
    safe_to_execute: bool = False
    safe_to_dry_run: bool = True
    blocked: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[ToolTraceItem] = Field(default_factory=list)


class ToolDryRunResult(AIpinhoModel):
    dry_run_id: str
    status: ToolResultStatus
    tool_results: list[ToolDryRunResultItem] = Field(default_factory=list)
    safe_to_execute: bool = False
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)
    trace: list[ToolTraceItem] = Field(default_factory=list)
