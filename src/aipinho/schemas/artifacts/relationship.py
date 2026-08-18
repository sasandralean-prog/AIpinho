from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


RelationshipFamily = Literal[
    "descriptive_sidecar_candidate",
    "visual_sidecar_candidate",
    "textual_sidecar_candidate",
    "metadata_sidecar_candidate",
    "collection_member_candidate",
    "variant_candidate",
    "derived_asset_candidate",
    "same_work_candidate",
    "unknown_related_asset_candidate",
]
RelationshipCandidateStatus = Literal["candidate", "rejected", "blocked", "observed", "validated_later"]
RelationshipConfidenceBand = Literal["insufficient", "low", "medium", "high", "conflicted"]
RelationshipValidationStatus = Literal["not_ready", "validation_ready", "validated", "rejected", "blocked", "conflicted"]


class RelationshipConfidence(AIpinhoModel):
    score: float = 0.0
    band: RelationshipConfidenceBand = "low"
    policy: dict[str, Any] = Field(default_factory=dict)


class RelationshipConfidenceModel(AIpinhoModel):
    model_id: str = Field(default_factory=lambda: f"relationship_confidence_model_{uuid4().hex}")
    raw_score: float = 0.0
    normalized_score: float = 0.0
    confidence_band: RelationshipConfidenceBand = "insufficient"
    signal_contributions: list[dict[str, Any]] = Field(default_factory=list)
    positive_signal_count: int = 0
    negative_signal_count: int = 0
    conflict_count: int = 0
    missing_signal_count: int = 0
    calibration_notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RelationshipProvenance(AIpinhoModel):
    source: str = "media_relationship_candidate_detector"
    producer_capability_id: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    normalization_refs: list[dict[str, Any]] = Field(default_factory=list)


class RelationshipProvenanceTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: f"relationship_provenance_trace_{uuid4().hex}")
    candidate_id: str
    source_entity_ref: dict[str, Any] = Field(default_factory=dict)
    target_entity_ref: dict[str, Any] = Field(default_factory=dict)
    producer_capability_id: str
    relationship_goal_id: str | None = None
    input_entities_ref: list[dict[str, Any]] = Field(default_factory=list)
    input_artifact_contract_ref: dict[str, Any] = Field(default_factory=dict)
    signals_used: list[dict[str, Any]] = Field(default_factory=list)
    signals_rejected: list[dict[str, Any]] = Field(default_factory=list)
    normalization_steps: list[dict[str, Any]] = Field(default_factory=list)
    policy_checks: list[dict[str, Any]] = Field(default_factory=list)
    arbitration_decision_ref: str | None = None
    evidence_record_refs: list[str] = Field(default_factory=list)
    created_at: str | None = None


class RelationshipLimitation(AIpinhoModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class RelationshipValidationHint(AIpinhoModel):
    required_validation: str = "relationship_final_validation"
    reason_code: str = "RELATIONSHIP_VALIDATION_REQUIRED"
    truth_eligible: bool = False


class RelationshipGoal(AIpinhoModel):
    goal_id: str = Field(default_factory=lambda: f"relationship_goal_{uuid4().hex}")
    contract_id: str | None = None
    artifact_id: str | None = None
    source_scope: dict[str, Any] = Field(default_factory=dict)
    target_scope: dict[str, Any] = Field(default_factory=dict)
    allowed_relation_families: list[str] = Field(default_factory=list)
    required_evidence_types: list[str] = Field(default_factory=list)
    forbidden_authority_shortcuts: list[str] = Field(default_factory=list)
    confidence_policy: dict[str, Any] = Field(default_factory=dict)
    truth_policy: dict[str, Any] = Field(default_factory=lambda: {"truth_eligible": False, "validation_required": True})
    created_by: str = "cvl_or_contract"


class RelationshipEvidenceSignal(AIpinhoModel):
    signal_id: str = Field(default_factory=lambda: f"relationship_signal_{uuid4().hex}")
    signal_type: str
    raw_value: Any | None = None
    normalized_value: Any | None = None
    normalization_trace: list[str] = Field(default_factory=list)
    source_entity_ref: dict[str, Any] = Field(default_factory=dict)
    target_entity_ref: dict[str, Any] = Field(default_factory=dict)
    confidence_contribution: float = 0.0
    confidence_weight: float = 1.0
    confidence_method: str = "weighted_signal_contribution"
    why_it_matters: str
    why_it_is_not_sufficient_alone: str = "A relationship candidate requires multiple compatible signals and later validation."
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    is_sufficient_alone: bool = False


class RelationshipNegativeEvidence(AIpinhoModel):
    negative_evidence_id: str = Field(default_factory=lambda: f"relationship_negative_evidence_{uuid4().hex}")
    candidate_id: str | None = None
    code: str
    description: str
    confidence_penalty: float = 0.0
    source_entity_ref: dict[str, Any] = Field(default_factory=dict)
    target_entity_ref: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class RelationshipConflict(AIpinhoModel):
    conflict_id: str = Field(default_factory=lambda: f"relationship_conflict_{uuid4().hex}")
    candidate_id: str | None = None
    code: str
    description: str
    severity: str = "medium"
    blocks_validation_ready: bool = True
    source_entity_ref: dict[str, Any] = Field(default_factory=dict)
    target_entity_ref: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class RelationshipEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"relationship_evidence_{uuid4().hex}")
    candidate_id: str
    signal_id: str | None = None
    signal_type: str
    signal_value: Any | None = None
    source_entity_id: str
    target_entity_id: str
    confidence_contribution: float = 0.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    is_sufficient_alone: bool = False
    limitations: list[str] = Field(default_factory=list)
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


class RelationshipCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"relationship_candidate_{uuid4().hex}")
    source_entity_id: str
    target_entity_id: str
    relation_family: str = "unknown_related_asset_candidate"
    relation_kind_candidate: str | None = None
    status: RelationshipCandidateStatus = "candidate"
    confidence: float = 0.0
    confidence_band: RelationshipConfidenceBand = "low"
    confidence_model: RelationshipConfidenceModel | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    provenance_trace_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    negative_evidence: list[RelationshipNegativeEvidence] = Field(default_factory=list)
    conflicts: list[RelationshipConflict] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    truth_eligible: bool = False
    validation_required: bool = True


class RelationshipObservation(AIpinhoModel):
    observation_id: str = Field(default_factory=lambda: f"relationship_observation_{uuid4().hex}")
    candidate_id: str
    observed_relation_family: str
    observed_relation_kind_candidate: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    provenance_trace_id: str | None = None
    confidence: float = 0.0
    confidence_model: RelationshipConfidenceModel | None = None
    coverage: float = 0.0
    producer_capability_id: str
    observer_id: str | None = None
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    truth_eligible: bool = False
    created_at: str | None = None


class RelationshipBinding(AIpinhoModel):
    binding_id: str = Field(default_factory=lambda: f"relationship_binding_{uuid4().hex}")
    status: str = "empty"
    bound_relationship_observations: list[dict[str, Any]] = Field(default_factory=list)
    relationship_provenance_traces: list[dict[str, Any]] = Field(default_factory=list)
    relationship_candidates_by_artifact: dict[str, int] = Field(default_factory=dict)
    relationship_evidence_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_confidence_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_conflict_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_negative_evidence_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_binding_quality: dict[str, Any] = Field(default_factory=dict)
    relationship_limitations: list[str] = Field(default_factory=list)
    truth_eligible: bool = False
    source: str = "RelationshipObservation"


class RelationshipValidationPolicy(AIpinhoModel):
    policy_id: str = Field(default_factory=lambda: f"relationship_validation_policy_{uuid4().hex}")
    allowed_relation_families: list[str] = Field(default_factory=list)
    minimum_signal_diversity: int = 2
    minimum_confidence: float = 0.5
    required_positive_signal_types: list[str] = Field(default_factory=list)
    forbidden_conflicts: list[str] = Field(default_factory=list)
    required_provenance_fields: list[str] = Field(default_factory=lambda: ["provenance_trace_id"])
    required_evidence_record_types: list[str] = Field(default_factory=lambda: ["relationship_observation"])
    negative_evidence_threshold: float = 0.35
    ambiguity_policy: dict[str, Any] = Field(default_factory=lambda: {"allow_ambiguous": False})
    truth_policy: dict[str, Any] = Field(default_factory=lambda: {"truth_eligible": False, "speaker_claim_allowed": False})
    allow_validated_status: bool = False


class RelationshipValidationResult(AIpinhoModel):
    validation_id: str = Field(default_factory=lambda: f"relationship_validation_{uuid4().hex}")
    candidate_id: str
    status: RelationshipValidationStatus = "not_ready"
    reason_codes: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    policy_id: str
    signals_passed: list[str] = Field(default_factory=list)
    signals_failed: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    provenance_ok: bool = False
    evidence_ok: bool = False
    truth_eligible: bool = False
    speaker_claim_allowed: bool = False
    limitations: list[str] = Field(default_factory=list)
