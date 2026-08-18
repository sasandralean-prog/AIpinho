from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ToolExecutionStatus = Literal["executed_readonly", "executed_governed", "blocked", "invalid", "degraded", "timeout"]


class ToolExecutionResult(AIpinhoModel):
    execution_id: str
    tool_id: str
    status: ToolExecutionStatus
    action: str | None = None
    capability: str | None = None
    workspace: str | None = None
    target_path: str | None = None
    content: str | None = None
    content_truncated: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    audit_event_id: str | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)
    side_effects: bool = False
    safe_to_execute: bool = False
