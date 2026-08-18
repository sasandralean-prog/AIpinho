from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class SuccessContractCreateRequest(AIpinhoModel):
    objective: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    completion_definition: str = ""
    priority: str = "normal"
    created_by: str = "aipinho"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuccessContract(AIpinhoModel):
    success_contract_id: str = Field(default_factory=lambda: f"success_contract_{uuid4().hex}")
    objective: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    completion_definition: str = ""
    priority: str = "normal"
    owner: str = "aipinho"
    status: str = "active"
    created_by: str = "aipinho"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalTaskCreateRequest(AIpinhoModel):
    provider: str
    objective: str
    context: dict[str, Any] = Field(default_factory=dict)
    expected_output: str = ""
    constraints: list[str] = Field(default_factory=list)
    deadline: str | None = None
    success_contract_id: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    workspace: str | None = None
    contract_type: str = "conversation"
    operation_type: str = "conversation"
    runtime_profile: str = "conversation"
    create_task_run: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalTaskContract(AIpinhoModel):
    external_task_id: str = Field(default_factory=lambda: f"external_task_{uuid4().hex}")
    provider: str
    objective: str
    context: dict[str, Any] = Field(default_factory=dict)
    expected_output: str = ""
    constraints: list[str] = Field(default_factory=list)
    deadline: str | None = None
    success_contract_id: str | None = None
    conversation_id: str | None = None
    related_task_run_id: str | None = None
    status: str = "received"
    authority: str = "aipinho"
    external_authority: str = "none"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalReviewFinding(AIpinhoModel):
    severity: str = "info"
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    recommendation: str | None = None


class ExternalReviewCreateRequest(AIpinhoModel):
    provider: str
    task_run_id: str | None = None
    external_task_id: str | None = None
    conversation_id: str | None = None
    status: str = "submitted"
    confidence: float = 0.0
    findings: list[ExternalReviewFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    next_action: str = "aipinho_decides"
    raw_summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalReviewContract(AIpinhoModel):
    review_id: str = Field(default_factory=lambda: f"external_review_{uuid4().hex}")
    provider: str
    contract_version: str = "external_review.v1"
    task_run_id: str | None = None
    external_task_id: str | None = None
    conversation_id: str | None = None
    received_at: str = Field(default_factory=utc_now_iso)
    status: str = "submitted"
    confidence: float = 0.0
    findings: list[ExternalReviewFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    next_action: str = "aipinho_decides"
    authority_decision: str = "received_for_internal_interpretation"
    may_execute: bool = False
    replaces_internal_reviewer: bool = False
    raw_summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalConversationCreateRequest(AIpinhoModel):
    provider: str
    session_id: str | None = None
    related_task_id: str | None = None
    related_review_id: str | None = None
    title: str = "External collaboration"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalConversationRecord(AIpinhoModel):
    conversation_id: str = Field(default_factory=lambda: f"external_conversation_{uuid4().hex}")
    provider: str
    session_id: str | None = None
    related_task_id: str | None = None
    related_review_id: str | None = None
    title: str = "External collaboration"
    status: str = "open"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalAdapterReviewRequest(AIpinhoModel):
    provider_output: str
    provider: str | None = None
    task_run_id: str | None = None
    external_task_id: str | None = None
    conversation_id: str | None = None
    confidence: float = 0.7
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalAdapterOutput(AIpinhoModel):
    adapter_id: str
    human_output: str
    machine_output: ExternalReviewCreateRequest
    status: str = "ready"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuccessEvaluationCreateRequest(AIpinhoModel):
    provider: str
    session_id: str | None = None
    task_run_id: str | None = None
    external_task_id: str | None = None
    status: str = "submitted"
    acceptance_score: float = 0.0
    blocking_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    needs_retry: bool = False
    ready: bool = False
    needs_human: bool = False
    next_action: str = "aipinho_decides"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuccessEvaluation(AIpinhoModel):
    evaluation_id: str = Field(default_factory=lambda: f"success_eval_{uuid4().hex}")
    provider: str
    session_id: str | None = None
    task_run_id: str | None = None
    external_task_id: str | None = None
    status: str = "submitted"
    acceptance_score: float = 0.0
    blocking_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    needs_retry: bool = False
    ready: bool = False
    needs_human: bool = False
    next_action: str = "aipinho_decides"
    received_at: str = Field(default_factory=utc_now_iso)
    may_execute: bool = False
    authority: str = "aipinho"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuccessContractRuntime(AIpinhoModel):
    success_contract_id: str | None = None
    goal: str
    definition_of_done: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    blocking_conditions: list[str] = Field(default_factory=list)
    non_blocking_conditions: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    maximum_iterations: int = 3
    current_iteration: int = 0
    status: str = "active"


class CollaborationMemory(AIpinhoModel):
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    external_messages: list[dict[str, Any]] = Field(default_factory=list)
    machine_outputs: list[dict[str, Any]] = Field(default_factory=list)
    human_outputs: list[dict[str, Any]] = Field(default_factory=list)
    reviews: list[str] = Field(default_factory=list)
    evaluations: list[str] = Field(default_factory=list)


class ContinuousCollaborationStartRequest(AIpinhoModel):
    provider: str
    task_run_id: str
    success_contract_id: str | None = None
    external_conversation_id: str | None = None
    maximum_iterations: int = 3
    expires_at: str | None = None
    subscribed_event_types: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContinuousCollaborationSession(AIpinhoModel):
    session_id: str = Field(default_factory=lambda: f"ccr_session_{uuid4().hex}")
    provider: str
    external_conversation_id: str | None = None
    task_run_id: str
    success_contract_id: str | None = None
    review_iteration: int = 0
    status: str = "active"
    started_at: str = Field(default_factory=utc_now_iso)
    last_activity: str = Field(default_factory=utc_now_iso)
    expires_at: str | None = None
    success_runtime: SuccessContractRuntime
    retry_state: dict[str, Any] = Field(default_factory=dict)
    last_review: str | None = None
    last_evaluation_id: str | None = None
    retry_count: int = 0
    reason: str = ""
    subscribed_event_types: list[str] = Field(default_factory=list)
    last_event_sequence: int = 0
    observed_events: list[dict[str, Any]] = Field(default_factory=list)
    memory: CollaborationMemory = Field(default_factory=CollaborationMemory)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContinuousCollaborationPollResponse(AIpinhoModel):
    session: ContinuousCollaborationSession
    universal_task_session: dict[str, Any] | None = None
    relevant_events: list[dict[str, Any]] = Field(default_factory=list)
    retry_strategy: str = "Continue"
    completion_checks: dict[str, Any] = Field(default_factory=dict)


class ExternalAdapterEvaluationRequest(AIpinhoModel):
    provider_output: str
    provider: str | None = None
    session_id: str | None = None
    task_run_id: str | None = None
    external_task_id: str | None = None
    confidence: float = 0.7
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalAdapterEvaluationOutput(AIpinhoModel):
    adapter_id: str
    human_output: str
    machine_output: SuccessEvaluationCreateRequest
    status: str = "ready"
    metadata: dict[str, Any] = Field(default_factory=dict)
