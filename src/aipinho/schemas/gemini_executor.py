from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class GeminiExecutorConfigStatus(AIpinhoModel):
    enabled: bool
    primary_key_configured: bool
    secondary_key_configured: bool
    configured_key_count: int = 0
    fallback_key_count_configured: int = 0
    default_model: str
    default_execution_mode: str = "governed_autorun"
    timeout_seconds: int
    max_prompt_chars: int
    max_output_chars: int
    allow_write: bool
    allow_shell: bool
    require_approval_for_write: bool
    require_approval_for_shell: bool
    use_memory_gateway: bool = True
    use_delegation: bool = True
    prefer_aipinho_executor: bool = True
    allow_direct_local_tools: bool = False
    autorun_enabled: bool = True
    autoreview_enabled: bool = True
    autoapproval_enabled: bool = True
    raw_default_visible: bool = False
    cloud_warning_visible: bool = True
    provider: str = "gemini"
    last_error_sanitized: str | None = None


class GeminiExecutorSession(AIpinhoModel):
    session_id: str = Field(default_factory=lambda: f"gemini_session_{uuid4().hex}")
    title: str = "Gemini Executor"
    provider: str = "gemini"
    agent_id: str = "gemini_executor"
    status: str = "idle"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class GeminiExecutorMessage(AIpinhoModel):
    message_id: str = Field(default_factory=lambda: f"gemini_msg_{uuid4().hex}")
    session_id: str
    role: str
    content: str
    operation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class GeminiExecutorRequest(AIpinhoModel):
    session_id: str
    prompt: str
    code_context: str | None = None
    workspace_context: str | None = None
    operation_type: str = "gemini_chat"
    requested_capabilities: list[str] = Field(default_factory=list)
    workspace_id: str | None = None
    target_paths: list[str] = Field(default_factory=list)
    model: str | None = None
    temperature: float | None = None
    max_output_chars: int | None = None


class GeminiStructuredAction(AIpinhoModel):
    action_type: str
    status: str
    reason: str
    capability: str | None = None
    requires_approval: bool = False
    preview_id: str | None = None
    command_id: str | None = None
    validation_required: bool = False
    policy_decision: dict[str, Any] = Field(default_factory=dict)


class GeminiExecutorResponse(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"gemini_req_{uuid4().hex}")
    session_id: str
    run_id: str | None = None
    operation_id: str = Field(default_factory=lambda: f"gemini_op_{uuid4().hex}")
    status: str
    provider: str = "gemini"
    model: str
    text: str
    structured_actions: list[GeminiStructuredAction] = Field(default_factory=list)
    proposed_patch: dict[str, Any] | None = None
    proposed_shell_commands: list[dict[str, Any]] = Field(default_factory=list)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    error_code: str | None = None
    human_error: str | None = None
    external_provider_notice: bool = True
    cloud_warning_visible: bool = True
    fallback_used: bool = False
    delegation_id: str | None = None
    child_run_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    memory_refs_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
