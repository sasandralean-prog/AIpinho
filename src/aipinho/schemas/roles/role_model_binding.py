from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


RoleModelGateV2Status = Literal["allowed", "blocked", "degraded", "requires_manual_confirmation"]
RoleInferenceStatus = Literal["preview", "completed", "blocked", "degraded", "rejected", "fallback_used", "requires_manual_confirmation"]


class RoleModelBinding(AIpinhoModel):
    role_id: str
    enabled: bool = True
    primary_model: str
    fallback_model: str | None = None
    secondary_model: str | None = None
    escalation_model: str | None = None
    escalation_models: list[str] = Field(default_factory=list)
    escalation_mode: str | None = None
    allowed_capabilities: list[str] = Field(default_factory=list)
    default_real_inference: bool = True
    manual_only: bool = False
    max_latency_class: str = "medium"
    output_contract: str
    is_default_coding_role: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    def escalation_candidates(self) -> list[str]:
        return [item for item in [self.escalation_model, *self.escalation_models] if item]


class DisabledRoleModelBinding(AIpinhoModel):
    role_id: str
    reason: str
    enabled: bool = False


class RoleModelGateDecisionV2(AIpinhoModel):
    allowed: bool = False
    status: RoleModelGateV2Status = "blocked"
    role_id: str
    capability_id: str | None = None
    selection_source: str | None = None
    selected_model_id: str | None = None
    provider_id: str | None = None
    fallback_model_id: str | None = None
    manual_escalation_required: bool = False
    manual_escalation_used: bool = False
    budget: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)


class RoleInferenceBudget(AIpinhoModel):
    budget_id: str = Field(default_factory=lambda: f"role_budget_{uuid4().hex}")
    role_id: str
    budget_class: str = "medium"
    max_prompt_chars: int = 12000
    max_context_chars: int = 8000
    max_output_tokens: int = 1024
    timeout_seconds: int = 90
    first_token_warning_seconds: int = 30
    prompt_chars: int = 0
    context_chars: int = 0
    exceeded: bool = False
    warnings: list[str] = Field(default_factory=list)


class RoleModelEscalation(AIpinhoModel):
    manual_escalation: bool = False
    operator_confirmed: bool = False
    latency_warning_acknowledged: bool = False
    reason: str | None = None
    requested_model_id: str | None = None


class RoleInferenceRequest(AIpinhoModel):
    role_id: str
    prompt: str = ""
    task_input: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    requested_model_id: str | None = None
    include_trace: bool = True
    dry_run: bool = False
    manual_escalation: bool = False
    operator_confirmed: bool = False
    latency_warning_acknowledged: bool = False
    reason: str | None = None
    output_contract: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RolePromptContract(AIpinhoModel):
    role_id: str
    model_id: str
    output_contract: str
    prompt_text: str
    safety_envelope: dict[str, Any] = Field(default_factory=dict)
    policy_envelope: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RoleOutputEvaluation(AIpinhoModel):
    status: str
    accepted: bool = False
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    retry_recommended: bool = False
    fallback_recommended: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class RoleModelFallback(AIpinhoModel):
    fallback_model_id: str | None = None
    fallback_allowed: bool = False
    fallback_used: bool = False
    reason: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)


class RoleInferenceTrace(AIpinhoModel):
    trace_id: str
    role_id: str
    events: list[dict[str, Any]] = Field(default_factory=list)


class RoleInferenceResult(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: f"role_model_run_{uuid4().hex}")
    role_id: str
    status: RoleInferenceStatus
    selected_model_id: str | None = None
    provider_id: str | None = None
    fallback_model_id: str | None = None
    fallback_used: bool = False
    manual_escalation_used: bool = False
    raw_output_hidden: bool = True
    output: str = ""
    evaluation: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    model_response_status: str | None = None
    real_inference_attempted: bool = False
    real_inference_completed: bool = False
    side_effects: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoleModelStatus(AIpinhoModel):
    enabled: bool = True
    mode: str = "controlled_real_inference_per_role"
    chat_auto_role_inference: bool = False
    tool_calling_enabled: bool = False
    workspace_write_enabled: bool = False
    vision_runtime_enabled: bool = False
    ocr_runtime_enabled: bool = False
    embedding_runtime_enabled: bool = False
    reranker_runtime_enabled: bool = False
    default_coding_role: str = "coder"
    default_coding_model: str = "qwen2_5_coder_7b_q4_k_m"
    large_models_manual_only: bool = True
    roles: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RoleModelRun(AIpinhoModel):
    result: RoleInferenceResult
    request: dict[str, Any] = Field(default_factory=dict)
    prompt_contract: dict[str, Any] = Field(default_factory=dict)
