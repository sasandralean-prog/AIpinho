from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


IngressStatus = Literal["complete", "partial", "missing", "invalid"]
StateMutationLevel = Literal["none", "immutable", "read_only", "temporary", "mutable", "destructive", "prohibited"]


class PromptNormalization(AIpinhoModel):
    normalization_id: str = Field(default_factory=lambda: f"prompt_norm_{uuid4().hex}")
    original_text: str
    normalized_text: str
    encoding_detected: str = "unicode_text"
    encoding_issues: list[str] = Field(default_factory=list)
    transformations: list[str] = Field(default_factory=list)
    text_variants: dict[str, str] = Field(default_factory=dict)
    confidence: float = 1.0


class SemanticProposition(AIpinhoModel):
    proposition_id: str = Field(default_factory=lambda: f"semantic_prop_{uuid4().hex}")
    proposition_type: str
    subject: str = ""
    predicate: str = ""
    object_value: Any = None
    polarity: Literal["positive", "negative", "neutral"] = "neutral"
    confidence: float = 1.0
    evidence_refs: list[str] = Field(default_factory=list)


class StateEffect(AIpinhoModel):
    effect_id: str = Field(default_factory=lambda: f"state_effect_{uuid4().hex}")
    target: str
    effect: StateMutationLevel = "none"
    confidence: float = 1.0
    evidence_refs: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class IntentCandidate(AIpinhoModel):
    intent_id: str
    operation_type: str
    confidence: float = 0.0
    supporting_propositions: list[str] = Field(default_factory=list)
    rejected_reason: str | None = None
    arbitration_score: float = 0.0


class IntentDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"intent_decision_{uuid4().hex}")
    selected_intent_id: str
    selected_operation_type: str
    candidates: list[IntentCandidate] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    reason_codes: list[str] = Field(default_factory=list)
    decision_source: str = "canonical_intent_router"


class OperationContractCandidate(AIpinhoModel):
    contract_type: str
    operation_type: str
    confidence: float = 0.0
    state_effect_alignment: str = "unknown"
    supporting_intent: str | None = None
    rejected_reason: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class OperationContractDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"operation_contract_decision_{uuid4().hex}")
    selected_contract_type: str
    selected_operation_type: str
    candidates: list[OperationContractCandidate] = Field(default_factory=list)
    relation_to_intent: str = "unknown"
    relation_to_state_effects: str = "unknown"
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    reason_codes: list[str] = Field(default_factory=list)
    decision_source: str = "governance_lifecycle"


class SemanticIngressDoctorReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"semantic_ingress_{uuid4().hex}")
    status: IngressStatus = "complete"
    prompt_normalization: PromptNormalization
    semantic_propositions: list[SemanticProposition] = Field(default_factory=list)
    state_effects: list[StateEffect] = Field(default_factory=list)
    intent_decision: IntentDecision
    operation_contract_decision: OperationContractDecision
    reason_codes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
