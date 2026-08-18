from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


DelegationDecision = Literal[
    "DIRECT_RESPONSE",
    "DELEGATE",
    "HYBRID",
    "BLOCK",
    "REQUIRES_APPROVAL",
]

DelegationStatus = Literal[
    "created",
    "started",
    "forwarded",
    "polling",
    "completed",
    "failed",
    "cancelled",
    "timeout",
]


class DelegationDecisionResult(AIpinhoModel):
    decision: DelegationDecision
    reason_code: str
    reason: str = ""
    executor: str = "aipinho"
    routing_policy: str = "runtime_decision_engine"
    requires_delegation_contract: bool = False
    requires_approval: bool = False
    blocked: bool = False
    evidence: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DelegationCreateRequest(AIpinhoModel):
    provider: str
    objective: str
    parent_run_id: str | None = None
    session_id: str | None = None
    workspace: str | None = None
    contract_type: str = "conversation"
    operation_type: str = "conversation"
    runtime_profile: str = "conversation"
    reason: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DelegationContract(AIpinhoModel):
    delegation_id: str = Field(default_factory=lambda: f"delegation_{uuid4().hex}")
    parent_run_id: str
    child_run_id: str
    executor: str = "aipinho"
    status: DelegationStatus = "created"
    reason: str = ""
    routing_policy: str = "runtime_decision_engine"
    workspace: str | None = None
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    polling_count: int = 0
    review_status: str = "not_started"
    speaker_truth_hash: str | None = None
    provider: str = "external_adapter"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DelegationTruthValidation(AIpinhoModel):
    status: str
    delegation_claimed: bool = False
    delegation_id: str | None = None
    violations: list[str] = Field(default_factory=list)
    reason_code: str = "ok"
    required_evidence: list[str] = Field(default_factory=list)
