from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

AuditExecutionStatus = Literal["executed_readonly", "executed_governed", "blocked", "invalid", "degraded", "timeout"]


class ExecutionAuditEvent(AIpinhoModel):
    audit_event_id: str
    execution_id: str
    tool_id: str
    action: str | None = None
    workspace: str | None = None
    target_path: str | None = None
    status: AuditExecutionStatus
    bytes_read: int = 0
    side_effects: bool = False
    policy_decision_id: str | None = None
    timestamp: str
    trace_summary: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
