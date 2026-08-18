from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class ObservabilityCard(AIpinhoModel):
    card_id: str
    title: str
    status: str = "unknown"
    severity: str = "info"
    summary: str
    count: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    safe_actions: list[dict[str, Any]] = Field(default_factory=list)


class MultiAgentStatusItem(AIpinhoModel):
    agent_id: str
    display_name: str
    status: str = "idle"
    session_count: int = 0
    run_count: int = 0
    active_run_id: str | None = None
    pending_approvals: int = 0
    warnings: list[str] = Field(default_factory=list)


class MultiAgentDashboard(AIpinhoModel):
    generated_at: str = Field(default_factory=utc_now_iso)
    backend_status: str = "unknown"
    ports: dict[str, Any] = Field(default_factory=dict)
    agents: list[MultiAgentStatusItem] = Field(default_factory=list)
    active_runs: list[dict[str, Any]] = Field(default_factory=list)
    active_delegations: list[dict[str, Any]] = Field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    auto_approvals: list[dict[str, Any]] = Field(default_factory=list)
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)
    validations: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    reports: list[dict[str, Any]] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    self_healing: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    tool_gateway: dict[str, Any] = Field(default_factory=dict)
    event_bus: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    safe_actions: list[dict[str, Any]] = Field(default_factory=list)
    cards: list[ObservabilityCard] = Field(default_factory=list)
    raw_default_visible: bool = False


class DebuggerEventView(AIpinhoModel):
    event_id: str
    run_id: str | None = None
    session_id: str | None = None
    agent_id: str | None = None
    event_type: str
    status: str = "unknown"
    severity: str = "info"
    human_message: str
    created_at: str | None = None
    source: str = "agent_event"
    visible_in_timeline: bool = True
    evidence_refs: list[str] = Field(default_factory=list)
    refs: dict[str, str] = Field(default_factory=dict)
    payload_sanitized: dict[str, Any] = Field(default_factory=dict)
    raw_available: bool = False


class DebuggerEventsResponse(AIpinhoModel):
    generated_at: str = Field(default_factory=utc_now_iso)
    events: list[DebuggerEventView] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    raw_default_visible: bool = False


class TraceGraphNode(AIpinhoModel):
    node_id: str
    node_type: str
    label: str
    status: str = "unknown"
    severity: str = "info"
    refs: dict[str, str] = Field(default_factory=dict)


class TraceGraphEdge(AIpinhoModel):
    source: str
    target: str
    relation: str


class TraceGraphResponse(AIpinhoModel):
    run_id: str
    generated_at: str = Field(default_factory=utc_now_iso)
    nodes: list[TraceGraphNode] = Field(default_factory=list)
    edges: list[TraceGraphEdge] = Field(default_factory=list)
    events: list[DebuggerEventView] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StateConsistencyIssue(AIpinhoModel):
    issue_id: str
    issue_type: str
    severity: str = "warning"
    entity_type: str
    entity_id: str
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    suggested_action: str | None = None


class StateConsistencyReport(AIpinhoModel):
    generated_at: str = Field(default_factory=utc_now_iso)
    status: str = "ok"
    issues: list[StateConsistencyIssue] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class DebugBundleExportRequest(AIpinhoModel):
    agent_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    include_events: bool = True
    include_trace: bool = True
    include_dashboard: bool = True
    include_consistency: bool = True


class DebugBundleExportResponse(AIpinhoModel):
    status: str
    artifact_id: str | None = None
    filename: str | None = None
    download_endpoint: str | None = None
    requires_token: bool = True
    summary: str
    warnings: list[str] = Field(default_factory=list)
