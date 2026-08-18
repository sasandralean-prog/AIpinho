from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


AgentMessageRole = Literal["user", "assistant", "tool", "status", "error", "system_summary"]
AgentMessageKind = Literal[
    "chat_message",
    "run_status",
    "tool_event",
    "approval_notice",
    "validation_notice",
    "artifact_notice",
    "delegation_notice",
    "final_answer",
    "error_message",
    "system_diagnostic",
]


class AgentProfile(AIpinhoModel):
    agent_id: str
    display_name: str
    provider: str
    role: str
    enabled: bool = True
    capabilities: list[str] = Field(default_factory=list)
    ui_tab: str | None = None
    supports_multimodal: bool = False
    supports_delegation: bool = False
    supports_autorun: bool = False
    supports_autoreview: bool = False
    supports_autoapproval: bool = False
    implementation_status: str = "profile_only"
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AgentRegistryStatus(AIpinhoModel):
    status: str
    profiles_loaded: int
    enabled_profiles: int
    disabled_profiles: int
    agent_ids: list[str] = Field(default_factory=list)


class AgentSessionCreateRequest(AIpinhoModel):
    title: str | None = None
    active_workspace_id: str | None = None
    project_profile_id: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AgentSessionUpdateRequest(AIpinhoModel):
    title: str | None = None
    archived: bool | None = None
    deleted: bool | None = None
    active_workspace_id: str | None = None
    project_profile_id: str | None = None
    metadata_sanitized: dict[str, Any] | None = None


class AgentSession(AIpinhoModel):
    session_id: str = Field(default_factory=lambda: f"agent_session_{uuid4().hex}")
    agent_id: str
    title: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    archived: bool = False
    deleted: bool = False
    active_workspace_id: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AgentMessageCreateRequest(AIpinhoModel):
    role: AgentMessageRole
    message_kind: AgentMessageKind = "chat_message"
    content_sanitized: str
    run_id: str | None = None
    event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    visible_in_normal_mode: bool = True
    raw_ref: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AgentMessage(AIpinhoModel):
    message_id: str = Field(default_factory=lambda: f"agent_msg_{uuid4().hex}")
    session_id: str
    agent_id: str
    role: AgentMessageRole
    message_kind: AgentMessageKind = "chat_message"
    content_sanitized: str
    created_at: str = Field(default_factory=utc_now_iso)
    run_id: str | None = None
    event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    visible_in_normal_mode: bool = True
    raw_ref: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AgentMessagePublic(AIpinhoModel):
    message_id: str
    session_id: str
    agent_id: str
    role: AgentMessageRole
    message_kind: AgentMessageKind
    content_sanitized: str
    created_at: str
    run_id: str | None = None
    event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    visible_in_normal_mode: bool = True
    raw_available: bool = False
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AgentRunCreateRequest(AIpinhoModel):
    operation_type: str
    parent_run_id: str | None = None
    delegation_id: str | None = None
    status: str = "created"
    workspace_id: str | None = None
    project_profile_id: str | None = None
    workspace_profile_id: str | None = None
    validation_profile_id: str | None = None
    command_profile_ids: list[str] = Field(default_factory=list)
    capabilities_requested: list[str] = Field(default_factory=list)
    validation_status: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    memory_refs_used: list[str] = Field(default_factory=list)
    memory_refs_written: list[str] = Field(default_factory=list)
    memory_candidates_created: list[str] = Field(default_factory=list)
    memory_warnings: list[str] = Field(default_factory=list)
    final_message_id: str | None = None
    error_code: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AgentRunUpdateRequest(AIpinhoModel):
    status: str | None = None
    completed_at: str | None = None
    validation_status: str | None = None
    artifact_ids: list[str] | None = None
    memory_refs_used: list[str] | None = None
    memory_refs_written: list[str] | None = None
    memory_candidates_created: list[str] | None = None
    memory_warnings: list[str] | None = None
    final_message_id: str | None = None
    error_code: str | None = None
    metadata_sanitized: dict[str, Any] | None = None


class AgentRun(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: f"agent_run_{uuid4().hex}")
    session_id: str
    agent_id: str
    parent_run_id: str | None = None
    delegation_id: str | None = None
    status: str = "created"
    operation_type: str
    workspace_id: str | None = None
    project_profile_id: str | None = None
    workspace_profile_id: str | None = None
    validation_profile_id: str | None = None
    command_profile_ids: list[str] = Field(default_factory=list)
    capabilities_requested: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    validation_status: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    memory_refs_used: list[str] = Field(default_factory=list)
    memory_refs_written: list[str] = Field(default_factory=list)
    memory_candidates_created: list[str] = Field(default_factory=list)
    memory_warnings: list[str] = Field(default_factory=list)
    final_message_id: str | None = None
    error_code: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AgentEventCreateRequest(AIpinhoModel):
    event_type: str
    status: str = "received"
    severity: str = "info"
    human_message: str
    technical_summary_sanitized: str | None = None
    payload_sanitized: dict[str, Any] = Field(default_factory=dict)
    visible_in_timeline: bool = True
    evidence_refs: list[str] = Field(default_factory=list)
    parent_event_id: str | None = None
    correlation_id: str | None = None
    tool_invocation_id: str | None = None
    delegation_id: str | None = None
    approval_id: str | None = None
    validation_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    progress_current: int | None = None
    progress_total: int | None = None
    raw_ref: str | None = None


class AgentEvent(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"agent_event_{uuid4().hex}")
    run_id: str
    session_id: str
    agent_id: str
    sequence: int = 0
    session_sequence: int = 0
    event_type: str
    status: str = "received"
    severity: str = "info"
    human_message: str
    technical_summary_sanitized: str | None = None
    payload_sanitized: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    visible_in_timeline: bool = True
    evidence_refs: list[str] = Field(default_factory=list)
    parent_event_id: str | None = None
    correlation_id: str | None = None
    tool_invocation_id: str | None = None
    delegation_id: str | None = None
    approval_id: str | None = None
    validation_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    progress_current: int | None = None
    progress_total: int | None = None
    raw_ref: str | None = None


class AgentTimelineItem(AIpinhoModel):
    event_id: str
    run_id: str
    session_id: str
    agent_id: str
    sequence: int
    session_sequence: int
    event_type: str
    title: str
    body: str
    severity: str
    status: str
    created_at: str
    copy_text: str
    raw_available: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class AgentPollingContract(AIpinhoModel):
    enabled: bool
    recommended_interval_seconds: int = 5
    reason: str = "idle"
    stop_when_status_in: list[str] = Field(default_factory=lambda: ["completed", "completed_with_warnings", "failed", "blocked", "cancelled"])


class AgentTimelineResponse(AIpinhoModel):
    agent_id: str
    session_id: str
    latest_event_id: str | None = None
    latest_sequence: int = 0
    has_more: bool = False
    run_status: str = "idle"
    active_run_id: str | None = None
    events: list[AgentEvent] = Field(default_factory=list)
    messages: list[AgentMessagePublic] = Field(default_factory=list)
    cards: list[AgentTimelineItem] = Field(default_factory=list)
    polling_recommended: bool = False
    next_poll_seconds: int = 5
    polling: AgentPollingContract


class AgentRunEventsResponse(AIpinhoModel):
    run_id: str
    agent_id: str
    session_id: str
    latest_event_id: str | None = None
    latest_sequence: int = 0
    status: str
    events: list[AgentEvent] = Field(default_factory=list)
    cards: list[AgentTimelineItem] = Field(default_factory=list)
    has_more: bool = False
    polling: AgentPollingContract


class MobileAgentViewModel(AIpinhoModel):
    agent_id: str
    session_id: str
    state: "AgentSessionState"
    messages: list[AgentMessagePublic] = Field(default_factory=list)
    events: list[AgentTimelineItem] = Field(default_factory=list)
    cards: list[AgentTimelineItem] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    raw_available: bool = False
    raw_default_visible: bool = False
    polling: AgentPollingContract
    active_run: AgentRun | None = None


class AgentSessionState(AIpinhoModel):
    agent_id: str
    session_id: str
    latest_run_id: str | None = None
    latest_operation_type: str | None = None
    latest_status: str = "idle"
    active_run: AgentRun | None = None
    pending_approval: dict[str, Any] | None = None
    validation_status: str | None = None
    artifact_count: int = 0
    message_count: int = 0
    last_event_id: str | None = None
    last_sequence: int = 0
    safety_label: str = "safe"
    raw_available: bool = False
    blocked_reason_code: str | None = None
    updated_at: str = Field(default_factory=utc_now_iso)
