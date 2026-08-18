from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


TraceSeverity = Literal["debug", "info", "warning", "error", "critical"]


class TraceEvent(AIpinhoModel):
    event_id: str
    trace_id: str
    timestamp: str = Field(default_factory=utc_now_iso)
    source: str = "agent_event"
    type: str
    text: str
    severity: TraceSeverity = "info"
    raw_ref: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    tool_invocation_id: str | None = None
    policy_ref: str | None = None
    approval_ref: str | None = None
    payload_sanitized: dict[str, Any] = Field(default_factory=dict)


class MultiIslandTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex}")
    user_session_id: str | None = None
    source_agent: str | None = None
    target_agent: str | None = None
    bridge_task_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    workspace: str | None = None
    intent_type: str | None = None
    operation_type: str | None = None
    mode: str | None = None
    status: str = "unknown"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    events: list[TraceEvent] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    locks: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    final_answer: str | None = None
    raw_default_visible: bool = False


class TraceExportRequest(AIpinhoModel):
    format: Literal["markdown", "json", "zip"] = "markdown"
    include_events: bool = True
    include_artifacts: bool = True
    include_refs_only: bool = True

