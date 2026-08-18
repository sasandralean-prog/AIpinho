from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


CognitiveCapability = Literal["language", "reasoning", "vision", "ocr", "embedding", "reranking", "code_generation", "code_review", "planning"]
CognitiveRisk = Literal["low", "medium", "high", "critical"]
CognitiveDecisionStatus = Literal["allowed", "requires_approval", "blocked"]
CognitiveEscalationAction = Literal["remain", "escalate", "request_human_validation", "block"]
CognitiveGovernanceStatus = Literal["allowed", "requires_approval", "blocked"]


class CognitivePolicy(AIpinhoModel):
    policy_id: str = Field(default_factory=lambda: f"cognitive_policy_{uuid4().hex}")
    name: str
    scope: str
    capability: CognitiveCapability
    allowed_models: list[str] = Field(default_factory=list)
    forbidden_models: list[str] = Field(default_factory=list)
    max_risk: CognitiveRisk = "medium"
    max_cost: float | None = None
    max_latency_ms: int | None = None
    requires_approval: bool = False
    requires_supervisor: bool = False
    requires_runtime_doctor: bool = False
    version: str = "1.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CapabilityPolicy(CognitivePolicy):
    pass


class InferencePolicy(CognitivePolicy):
    inference_enabled: bool = True


class ReasoningPolicy(CognitivePolicy):
    max_reasoning_effort: Literal["low", "medium", "high", "xhigh"] = "medium"


class ModelPolicy(CognitivePolicy):
    provider_scope: str = "local_or_governed"


class RiskPolicy(CognitivePolicy):
    escalation_required_for: list[CognitiveRisk] = Field(default_factory=lambda: ["high", "critical"])


class CognitiveEvaluationRequest(AIpinhoModel):
    capability: CognitiveCapability
    model: str | None = None
    risk: CognitiveRisk = "low"
    estimated_cost: float | None = None
    estimated_latency_ms: int | None = None
    scope: str = "runtime"
    operator_approved: bool = False
    supervisor_available: bool = False
    runtime_doctor_available: bool = False


class CognitivePolicyDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"cognitive_decision_{uuid4().hex}")
    status: CognitiveDecisionStatus
    policy_id: str
    capability: CognitiveCapability
    model: str | None = None
    allowed: bool = False
    requires_approval: bool = False
    requires_supervisor: bool = False
    requires_runtime_doctor: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CognitivePolicyList(AIpinhoModel):
    version: str = "1.0"
    count: int
    policies: list[CognitivePolicy] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False


class CognitiveRoutingRequest(AIpinhoModel):
    isr: dict[str, Any] = Field(default_factory=dict)
    contracts: dict[str, Any] = Field(default_factory=dict)
    role: str
    capability: CognitiveCapability | None = None
    policy: dict[str, Any] = Field(default_factory=dict)
    scope: str = "runtime"
    risk: CognitiveRisk = "low"
    estimated_cost: float | None = None
    estimated_latency_ms: int | None = None
    operator_approved: bool = False
    supervisor_available: bool = False
    runtime_doctor_available: bool = False


class RoutingDecision(AIpinhoModel):
    route_id: str = Field(default_factory=lambda: f"cognitive_route_{uuid4().hex}")
    status: CognitiveDecisionStatus
    role: str
    capability: CognitiveCapability
    model: str | None = None
    policy_id: str
    requires_supervisor: bool = False
    requires_approval: bool = False
    can_escalate: bool = False
    escalation_models: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False
    prompt_interpreted: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CognitiveRouteList(AIpinhoModel):
    count: int
    routes: list[RoutingDecision] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False


class EscalationPolicy(AIpinhoModel):
    policy_id: str = Field(default_factory=lambda: f"cognitive_escalation_policy_{uuid4().hex}")
    name: str = "Default cognitive escalation policy"
    scope: str = "runtime"
    capability: CognitiveCapability | None = None
    low_confidence_threshold: float = 0.45
    human_validation_confidence_threshold: float = 0.6
    high_complexity_threshold: float = 0.7
    max_risk_without_block: CognitiveRisk = "high"
    requires_human_for_high_risk: bool = True
    version: str = "1.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CognitiveEscalationRequest(AIpinhoModel):
    isr: dict[str, Any] = Field(default_factory=dict)
    contracts: dict[str, Any] = Field(default_factory=dict)
    routing_decision: RoutingDecision
    confidence: float | None = None
    risk: CognitiveRisk = "low"
    scope: str = "runtime"


class EscalationDecision(AIpinhoModel):
    escalation_id: str = Field(default_factory=lambda: f"cognitive_escalation_{uuid4().hex}")
    action: CognitiveEscalationAction
    capability: CognitiveCapability
    role: str
    routing_decision_id: str
    current_model: str | None = None
    target_model: str | None = None
    confidence: float
    complexity: float
    risk: CognitiveRisk
    policy_id: str
    requires_human_validation: bool = False
    blocked: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CognitiveEscalationHistory(AIpinhoModel):
    count: int
    decisions: list[EscalationDecision] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False


class CognitiveGovernanceRequest(AIpinhoModel):
    isr: dict[str, Any] = Field(default_factory=dict)
    contracts: dict[str, Any] = Field(default_factory=dict)
    role: str
    capability: CognitiveCapability | None = None
    risk: CognitiveRisk = "low"
    confidence: float | None = None
    estimated_cost: float | None = None
    estimated_latency_ms: int | None = None
    scope: str = "runtime"
    operator_approved: bool = False
    supervisor_available: bool = False
    runtime_doctor_available: bool = False


class GovernanceEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"cognitive_governance_evidence_{uuid4().hex}")
    source: Literal["semantic_runtime", "policy_engine", "router", "escalation", "governance_controller"]
    summary: str
    refs: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GovernanceSession(AIpinhoModel):
    governance_session_id: str = Field(default_factory=lambda: f"cognitive_governance_session_{uuid4().hex}")
    role: str
    capability: CognitiveCapability
    scope: str = "runtime"
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GovernanceAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"cognitive_governance_audit_{uuid4().hex}")
    governance_session_id: str
    route_id: str
    policy_decision_id: str
    escalation_id: str
    status: CognitiveGovernanceStatus
    evidence_ids: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GovernanceDecision(AIpinhoModel):
    governance_decision_id: str = Field(default_factory=lambda: f"cognitive_governance_decision_{uuid4().hex}")
    status: CognitiveGovernanceStatus
    allowed: bool = False
    role: str
    capability: CognitiveCapability
    model: str | None = None
    requires_approval: bool = False
    requires_supervisor: bool = False
    requires_runtime_doctor: bool = False
    requires_human_validation: bool = False
    route: RoutingDecision
    policy_decision: CognitivePolicyDecision
    escalation: EscalationDecision
    session: GovernanceSession
    evidence: list[GovernanceEvidence] = Field(default_factory=list)
    audit: GovernanceAudit
    reason_codes: list[str] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CognitiveGovernanceHistory(AIpinhoModel):
    count: int
    decisions: list[GovernanceDecision] = Field(default_factory=list)
    deterministic: bool = True
    inference_executed: bool = False
