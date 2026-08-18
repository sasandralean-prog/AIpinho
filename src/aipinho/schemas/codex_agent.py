from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class CodexAgentConfigStatus(AIpinhoModel):
    enabled: bool
    cli_path: str
    cli_detected: bool
    cli_status: str
    default_workdir: str
    timeout_seconds: int
    require_approval_for_write: bool
    require_approval_for_shell: bool
    allow_read: bool
    allow_write: bool
    allow_shell: bool
    use_staging_worktree: bool
    max_output_chars: int
    history_retention_days: int
    history_context_messages: int
    history_context_chars: int
    mobile_enabled: bool = True
    autorun_enabled: bool = True
    autoreview_enabled: bool = True
    autoapproval_enabled: bool = True
    autopilot_mode: str = "governed_autorun"
    polling_interval_seconds: int = 5
    max_run_seconds: int = 1800
    max_shell_seconds: int = 600
    max_events_per_poll: int = 100
    max_output_chars_per_event: int = 12000
    allow_artifact_upload: bool = True
    allow_artifact_download: bool = True
    autorun_max_steps: int = 20
    autorun_max_file_writes: int = 50
    autorun_max_shell_commands: int = 20
    autorun_max_artifacts: int = 20
    emergency_stop_enabled: bool = True
    last_error_sanitized: str | None = None


class CodexChatSession(AIpinhoModel):
    session_id: str = Field(default_factory=lambda: f"codex_session_{uuid4().hex}")
    title: str = "Codex Agent"
    agent_id: str = "codex_agent"
    status: str = "idle"
    archived: bool = False
    deleted: bool = False
    active_workspace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CodexChatMessage(AIpinhoModel):
    message_id: str = Field(default_factory=lambda: f"codex_msg_{uuid4().hex}")
    session_id: str
    role: str
    content: str
    run_id: str | None = None
    event_id: str | None = None
    operation_id: str | None = None
    trace_id: str | None = None
    message_kind: str = "chat"
    visible_in_mobile: bool = True
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    sanitized: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class CodexToolRequest(AIpinhoModel):
    tool_name: str
    workspace_id: str | None = None
    path_ref: str | None = None
    operation_type: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class CodexAgentRequest(AIpinhoModel):
    session_id: str
    prompt: str
    workspace_context: str | None = None
    operation_type: str = "codex_chat"
    requested_capabilities: list[str] = Field(default_factory=list)
    tool_requests: list[CodexToolRequest] = Field(default_factory=list)
    model: str | None = None
    max_output_chars: int | None = None
    autorun_enabled: bool | None = None
    autoreview_enabled: bool | None = None
    autoapproval_enabled: bool | None = None


class CodexAgentResponse(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"codex_req_{uuid4().hex}")
    session_id: str
    run_id: str | None = None
    operation_id: str = Field(default_factory=lambda: f"codex_op_{uuid4().hex}")
    status: str
    agent_id: str = "codex_agent"
    text: str
    cli_status: str
    provider: str = "codex_cli"
    latency_ms: int | None = None
    cli_event_count: int = 0
    structured_actions: list[dict[str, Any]] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    validation_status: str | None = None
    final_message_id: str | None = None
    error_code: str | None = None
    human_error: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class CodexRun(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: f"codex_run_{uuid4().hex}")
    session_id: str
    status: str = "created"
    user_prompt: str
    workspace_id: str | None = None
    workspace_path: str | None = None
    requested_capabilities: list[str] = Field(default_factory=list)
    autorun_enabled: bool = False
    autoreview_enabled: bool = False
    autoapproval_enabled: bool = False
    autopilot_mode: str = "off"
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    final_message_id: str | None = None
    validation_status: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    error_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexRunEvent(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"codex_event_{uuid4().hex}")
    run_id: str
    session_id: str
    sequence: int = 0
    event_type: str
    status: str = "info"
    title: str
    human_message: str
    technical_summary_sanitized: str | None = None
    payload_sanitized: dict[str, Any] = Field(default_factory=dict)
    visible_in_mobile: bool = True
    severity: str = "info"
    progress_current: int | None = None
    progress_total: int | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class CodexArtifact(AIpinhoModel):
    artifact_id: str
    session_id: str
    run_id: str | None = None
    filename: str
    content_type: str = "application/octet-stream"
    size: int = 0
    origin: str = "codex_generated"
    backend_ref: str | None = None
    requires_token: bool = True
    download_endpoint: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexAutoApprovalDecision(AIpinhoModel):
    auto_approval_id: str = Field(default_factory=lambda: f"codex_autoapproval_{uuid4().hex}")
    run_id: str
    session_id: str
    agent_id: str = "codex_agent"
    action_type: str
    capability: str
    workspace_id: str | None = None
    workspace_role: str | None = None
    risk_level: str = "low"
    policy_name: str = "codex_agent_autoapproval_policy"
    policy_decision_id: str | None = None
    reason: str
    approved: bool
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
