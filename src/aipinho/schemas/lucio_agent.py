from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


LucioRoute = Literal[
    "direct_response",
    "delegate_codex",
    "delegate_aipinho",
    "blocked",
    "answer_directly",
    "ask_clarification",
    "create_plan_only",
    "request_better_image",
    "request_missing_artifact",
]

LucioRouteType = Literal[
    "answer_directly",
    "ask_clarification",
    "delegate_to_codex",
    "delegate_to_aipinho",
    "create_plan_only",
    "block",
    "request_better_image",
    "request_missing_artifact",
]


class LucioArtifactInput(AIpinhoModel):
    artifact_id: str
    filename: str | None = None
    content_type: str | None = None
    purpose: str = "evidence"
    redaction_status: str = "unknown"
    preview_available: bool = False


class LucioAgentRequest(AIpinhoModel):
    session_id: str
    prompt: str
    operation_type: str = "lucio_chat"
    requested_capabilities: list[str] = Field(default_factory=list)
    workspace_id: str | None = None
    target_paths: list[str] = Field(default_factory=list)
    artifacts: list[LucioArtifactInput] = Field(default_factory=list)
    execution_mode: str | None = None
    model: str | None = None
    max_output_chars: int | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class LucioVisualArtifact(AIpinhoModel):
    artifact_id: str
    filename: str | None = None
    content_type: str | None = None
    size: int | None = None
    preview_available: bool = False
    requires_token: bool = True
    source_session_id: str | None = None
    source_agent_id: str = "lucio"
    redaction_status: str = "unknown"
    evidence_ref: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class LucioMultimodalMessage(AIpinhoModel):
    message_id: str = Field(default_factory=lambda: f"lucio_mm_msg_{uuid4().hex}")
    session_id: str
    agent_id: str = "lucio"
    user_text: str
    artifact_refs: list[str] = Field(default_factory=list)
    image_artifact_ids: list[str] = Field(default_factory=list)
    file_artifact_ids: list[str] = Field(default_factory=list)
    source: str = "user"
    content_types: list[str] = Field(default_factory=list)
    user_goal: str | None = None
    privacy_level: str = "public_safe"
    redaction_status: str = "not_required"
    multimodal_capability_required: bool = False
    route_decision_id: str | None = None
    delegation_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class LucioRouteDecision(AIpinhoModel):
    route_decision_id: str = Field(default_factory=lambda: f"lucio_route_{uuid4().hex}")
    route: LucioRoute
    route_type: LucioRouteType | None = None
    target_agent_id: str | None = None
    delegated_operation: str | None = None
    confidence: str = "medium"
    reasons: list[str] = Field(default_factory=list)
    reason_sanitized: str | None = None
    requested_capabilities: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    detected_intent: str | None = None
    input_modalities: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    clarification_question: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_source_count: int = 0
    requires_local_execution: bool = False


class LucioAgentResponse(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"lucio_req_{uuid4().hex}")
    session_id: str
    run_id: str
    status: str
    provider: str = "openai"
    model: str
    text: str
    public_reasoning_summary: str
    route_decision: LucioRouteDecision
    multimodal_message: LucioMultimodalMessage | None = None
    visual_artifacts: list[LucioVisualArtifact] = Field(default_factory=list)
    delegation_id: str | None = None
    child_run_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    memory_refs_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    external_provider_notice: bool = True
    raw_default_visible: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class LucioConfigStatus(AIpinhoModel):
    enabled: bool
    api_key_configured: bool
    provider: str = "disabled"
    provider_status: str = "disabled_by_config"
    provider_required: bool = False
    openai_enabled: bool = False
    provider_configured: bool = False
    auth_present: bool = False
    base_url_configured: bool = False
    project_configured: bool = False
    organization_configured: bool = False
    default_model: str
    model_configured: bool = False
    model_available_or_unknown: str = "unknown"
    timeout_seconds: int
    max_prompt_chars: int
    max_output_chars: int
    use_memory_gateway: bool
    use_delegation: bool
    default_execution_mode: str
    allow_direct_local_tools: bool
    raw_default_visible: bool = False
    external_provider_notice: bool = True
    multimodal_enabled: bool = False
    multimodal_provider: str | None = None
    multimodal_allowed_content_types: list[str] = Field(default_factory=list)
    multimodal_store_images: bool = True
    multimodal_memory_write_default: bool = False
    multimodal_redaction_required: bool = True
    multimodal_delegation_enabled: bool = True
    visible_in_ux: bool = False
    allow_new_sessions: bool = False
    last_error_sanitized: str | None = None
    last_provider_error: str | None = None
    last_provider_error_at: str | None = None
