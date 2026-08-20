from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.artifacts.relationship import (
    RelationshipCandidate,
    RelationshipEvidence,
    RelationshipGoal,
    RelationshipObservation,
    RelationshipProvenanceTrace,
)


CandidateSelectionStatus = Literal["selected", "candidate", "rejected"]
ObservationState = Literal["observed", "missing", "unsupported", "ambiguous", "low_confidence"]
CoverageStatus = Literal["complete", "partial", "blocked", "not_applicable"]
ObservationTaskStatus = Literal[
    "PLANNED",
    "BLOCKED_NO_CAPABILITY",
    "READY_FOR_OBSERVER",
    "EXECUTING",
    "EXECUTED",
    "FAILED",
    "BLOCKED_PRECONDITION",
    "BLOCKED_POLICY",
    "BLOCKED_TIMEOUT",
    "BLOCKED_OBSERVER_ERROR",
]
AttributeRequiredness = Literal["required", "optional", "nullable", "computed", "derived", "best_effort"]
CapabilityMatchStatus = Literal[
    "MATCHED",
    "NO_MATCHING_CAPABILITY",
    "PARTIAL_MATCH",
    "AMBIGUOUS_MATCH",
    "PRECONDITION_FAILED",
    "POLICY_BLOCKED",
]
CapabilityArbitrationStatus = Literal[
    "SELECTED",
    "BLOCKED_NO_CAPABILITY",
    "BLOCKED_PRECONDITION",
    "BLOCKED_POLICY",
    "BLOCKED_AMBIGUOUS",
]
ObservationStrategyKind = Literal[
    "read_existing_attribute",
    "calculate",
    "infer_from_evidence",
    "query_component",
    "execute_observer",
    "combine_evidence",
]
CapabilityDecisionStatus = Literal[
    "selected",
    "no_matching_capability",
    "capability_rejected",
    "multiple_capabilities_available",
    "low_confidence",
    "not_required",
]
ObservationExecutionStatus = Literal[
    "PLANNED",
    "READY_FOR_OBSERVER",
    "EXECUTING",
    "EXECUTED",
    "FAILED",
    "BLOCKED_NO_CAPABILITY",
    "BLOCKED_PRECONDITION",
    "BLOCKED_POLICY",
    "BLOCKED_TIMEOUT",
    "BLOCKED_OBSERVER_ERROR",
]
ObservationExecutionDisposition = Literal[
    "deferred_by_compile_policy",
    "executed_by_post_compile_stage",
    "blocked_by_post_compile_stage",
]
ObservationExecutionErrorCode = Literal[
    "OBSERVER_NOT_BOUND",
    "OBSERVER_INPUT_SCHEMA_INVALID",
    "OBSERVER_OUTPUT_SCHEMA_INVALID",
    "OBSERVER_TIMEOUT",
    "OBSERVER_RUNTIME_ERROR",
    "OBSERVER_POLICY_BLOCKED",
    "OBSERVER_PRODUCED_NO_EVIDENCE",
    "OBSERVER_CONFIDENCE_TOO_LOW",
    "MEDIA_CAPABILITY_ENTITY_ROLE_REJECTED",
    "MEDIA_CAPABILITY_ROOT_ROLE_REJECTED",
    "MEDIA_CAPABILITY_FILE_PATH_MISSING",
    "MEDIA_METADATA_CAPABILITY_NOT_REGISTERED",
    "MEDIA_METADATA_OBSERVER_BINDING_MISSING",
    "MEDIA_METADATA_BACKEND_NOT_AVAILABLE",
    "MEDIA_METADATA_DEPENDENCY_MISSING",
    "MUTAGEN_NOT_IMPORTABLE",
    "FFPROBE_NOT_AVAILABLE",
    "FFPROBE_TIMEOUT",
    "FFPROBE_INVALID_JSON",
    "FFPROBE_RUNTIME_ERROR",
    "MEDIA_BACKEND_NOT_AVAILABLE",
    "MEDIA_BACKEND_UNSUPPORTED_FORMAT",
    "MEDIA_BACKEND_NO_EVIDENCE",
    "MEDIA_BACKEND_PARTIAL_EVIDENCE",
    "MEDIA_BACKEND_CONTRADICTION",
    "MEDIA_BACKEND_LOW_CONFIDENCE",
    "MEDIA_BACKEND_RUNTIME_ERROR",
    "EVIDENCE_COVERAGE_INSUFFICIENT",
]
KnowledgeState = Literal[
    "UNKNOWN",
    "DISCOVERED",
    "OBSERVED",
    "INFERRED",
    "CORROBORATED",
    "VERIFIED",
    "CONFLICTED",
    "INSUFFICIENT_EVIDENCE",
    "REJECTED",
]
SemanticAssertionKind = Literal["observation", "inference", "hypothesis", "validated_knowledge"]
SemanticQualityStatus = Literal["pass", "warning", "fail", "not_applicable"]


class ContractObservationPlan(AIpinhoModel):
    plan_id: str = Field(default_factory=lambda: f"contract_observation_plan_{uuid4().hex}")
    contract_id: str | None = None
    artifact_id: str | None = None
    artifact_logical_path: str | None = None
    artifact_kind: str | None = None
    task_run_id: str | None = None
    expected_kind: str | None = None
    expected_entities: list[dict[str, Any]] = Field(default_factory=list)
    expected_relationships: list[dict[str, Any]] = Field(default_factory=list)
    expected_entity_role: str | None = None
    expected_entity_domain: str | None = None
    allowed_root_roles: list[str] = Field(default_factory=list)
    excluded_entity_roles: list[str] = Field(default_factory=list)
    entity_selection_contract: dict[str, Any] = Field(default_factory=dict)
    expected_attributes: list[str] = Field(default_factory=list)
    attribute_contracts: list["AttributeDescriptor"] = Field(default_factory=list)
    expected_cardinality: dict[str, Any] = Field(default_factory=dict)
    priorities: dict[str, int] = Field(default_factory=dict)
    minimum_confidence: float = 0.0
    constraints: dict[str, Any] = Field(default_factory=dict)
    unbound_reason: str | None = None


class AttributeIdentityNormalizationTrace(AIpinhoModel):
    raw_label: str
    display_label: str | None = None
    normalized_label: str
    canonical_key: str
    match_method: str
    known_alias_source: str | None = None
    confidence: float = 0.0
    loss_tolerance_used: bool = False
    mojibake_detected: bool = False
    accepted: bool = False
    reason_code: str


class AttributeDescriptor(AIpinhoModel):
    descriptor_id: str = Field(default_factory=lambda: f"attribute_descriptor_{uuid4().hex}")
    canonical_key: str
    display_label: str
    raw_label: str
    locale: str | None = None
    semantic_type: str = "contract_declared_attribute"
    value_type: str = "string"
    requiredness: AttributeRequiredness = "required"
    nullable: bool = False
    evidence_required: bool = True
    coverage_threshold: float = 1.0
    aliases: list[str] = Field(default_factory=list)
    normalization_notes: list[str] = Field(default_factory=list)
    normalization_trace: AttributeIdentityNormalizationTrace | None = None


AttributeIdentity = AttributeDescriptor
ArtifactAttributeContract = AttributeDescriptor


class CandidateEntity(AIpinhoModel):
    entity_id: str
    entity_kind: str
    source: str | None = None
    source_root_role: str | None = None
    entity_role: str | None = None
    entity_domain_hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    selection_eligibility: dict[str, Any] = Field(default_factory=dict)
    exclusion_reasons: list[str] = Field(default_factory=list)
    policy_rejection_reasons: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    matching_reason: str
    contract_relevance: float = 0.0
    ambiguity_level: float = 0.0
    covered_attributes: list[str] = Field(default_factory=list)
    potentially_observable_attributes: list[str] = Field(default_factory=list)
    missing_attributes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    status: CandidateSelectionStatus = "candidate"


class CandidateEntitySet(AIpinhoModel):
    candidate_set_id: str = Field(default_factory=lambda: f"candidate_entity_set_{uuid4().hex}")
    source_entity_set_id: str | None = None
    contract_observation_plan_id: str | None = None
    candidates: list[CandidateEntity] = Field(default_factory=list)
    selected_entity_ids: list[str] = Field(default_factory=list)
    semantic_gaps: list[dict[str, Any]] = Field(default_factory=list)


class SpecializationHypothesis(AIpinhoModel):
    hypothesis_id: str = Field(default_factory=lambda: f"specialization_hypothesis_{uuid4().hex}")
    entity_id: str
    base_entity_kind: str
    hypothesized_kind: str
    confidence: float = 0.0
    matching_reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False


class AttributeObservationRequirement(AIpinhoModel):
    attribute_name: str
    canonical_key: str | None = None
    display_label: str | None = None
    raw_label: str | None = None
    requiredness: AttributeRequiredness = "required"
    required: bool = True
    nullable: bool = False
    evidence_required: bool = True
    observed: bool = False
    confidence: float = 0.0
    priority: int = 0
    observer_capability_ids: list[str] = Field(default_factory=list)
    observation_goal_id: str | None = None
    strategy_ids: list[str] = Field(default_factory=list)
    capability_match_ids: list[str] = Field(default_factory=list)
    capability_decision_id: str | None = None
    gap_reason: str | None = None
    explanation: str | None = None
    recommendation: str | None = None


class ObservationGoal(AIpinhoModel):
    goal_id: str = Field(default_factory=lambda: f"observation_goal_{uuid4().hex}")
    contract_id: str | None = None
    artifact_id: str | None = None
    artifact_logical_path: str | None = None
    artifact_kind: str | None = None
    task_run_id: str | None = None
    entity_ref: dict[str, Any] = Field(default_factory=dict)
    contract_observation_plan_id: str | None = None
    attribute_name: str
    canonical_key: str | None = None
    display_label: str | None = None
    raw_label: str | None = None
    attribute_contract: AttributeDescriptor | None = None
    expected_semantic_type: str | None = None
    required_evidence_type: str | None = None
    required_confidence: float = 0.0
    required_coverage: float = 0.0
    reason: str | None = None
    source_contract_ref: dict[str, Any] = Field(default_factory=dict)
    target_entity_ids: list[str] = Field(default_factory=list)
    target_entity_kinds: list[str] = Field(default_factory=list)
    minimum_confidence: float = 0.0
    deadline: str | None = None
    importance: int = 0
    criticality: str = "required"
    contract_origin: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    unbound_reason: str | None = None


class ObservationStrategy(AIpinhoModel):
    strategy_id: str = Field(default_factory=lambda: f"observation_strategy_{uuid4().hex}")
    goal_id: str
    contract_id: str | None = None
    artifact_id: str | None = None
    artifact_logical_path: str | None = None
    artifact_kind: str | None = None
    task_run_id: str | None = None
    strategy_kind: ObservationStrategyKind
    strategy_type: str | None = None
    attribute_name: str
    canonical_key: str | None = None
    display_label: str | None = None
    target_entity_ids: list[str] = Field(default_factory=list)
    required_capability_kind: str
    candidate_capability_tags: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    required_attributes: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    required_preconditions: list[str] = Field(default_factory=list)
    satisfied_preconditions: list[str] = Field(default_factory=list)
    missing_preconditions: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    evidence_types: list[str] = Field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 0
    estimated_latency: int | None = None
    expected_confidence: float = 0.0
    estimated_confidence: float | None = None
    deterministic: bool = True
    limitations: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    rationale: str


class ObservationCapability(AIpinhoModel):
    capability_id: str
    name: str
    version: str = "1"
    domain: str = "generic"
    produces: list[str] = Field(default_factory=list)
    consumes: list[str] = Field(default_factory=list)
    observable_attributes: list[str] = Field(default_factory=list)
    supported_attribute_names: list[str] = Field(default_factory=list)
    compatible_entity_kinds: list[str] = Field(default_factory=lambda: ["*"])
    supported_entity_types: list[str] = Field(default_factory=list)
    evidence_types: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    supported_strategies: list[ObservationStrategyKind] = Field(default_factory=list)
    estimated_cost: float = 0.0
    latency_ms: int = 0
    typical_confidence: float = 0.0
    confidence_profile: dict[str, Any] = Field(default_factory=dict)
    cost_profile: dict[str, Any] = Field(default_factory=dict)
    latency_profile: dict[str, Any] = Field(default_factory=dict)
    determinism: str = "deterministic"
    risk_level: str = "low"
    requires_approval: bool = False
    observer_binding: dict[str, Any] = Field(default_factory=dict)
    status: str = "available"
    limitations: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    suggested_priority: int = 0
    available: bool = True


class CapabilityMatch(AIpinhoModel):
    match_id: str = Field(default_factory=lambda: f"capability_match_{uuid4().hex}")
    goal_id: str
    strategy_id: str
    capability_id: str | None = None
    contract_id: str | None = None
    artifact_id: str | None = None
    artifact_logical_path: str | None = None
    artifact_kind: str | None = None
    task_run_id: str | None = None
    strategy_ids: list[str] = Field(default_factory=list)
    attribute_name: str | None = None
    canonical_key: str | None = None
    match_status: CapabilityMatchStatus = "MATCHED"
    match_score: float = 0.0
    coverage_score: float = 0.0
    confidence_score: float = 0.0
    score: float = 0.0
    score_reason: str
    attributes_covered: list[str] = Field(default_factory=list)
    attributes_missing: list[str] = Field(default_factory=list)
    required_preconditions: list[str] = Field(default_factory=list)
    satisfied_preconditions: list[str] = Field(default_factory=list)
    missing_preconditions: list[str] = Field(default_factory=list)
    unsupported_attributes: list[str] = Field(default_factory=list)
    unsupported_entity_type: str | None = None
    unsupported_evidence_type: str | None = None
    blocking_reason: str | None = None
    explanation: str | None = None
    conflicts: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    available: bool = True


class CapabilityDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"capability_decision_{uuid4().hex}")
    goal_id: str
    contract_id: str | None = None
    artifact_id: str | None = None
    artifact_logical_path: str | None = None
    artifact_kind: str | None = None
    task_run_id: str | None = None
    status: CapabilityDecisionStatus
    decision_status: CapabilityArbitrationStatus | None = None
    decision_reason: str | None = None
    selected_capability_id: str | None = None
    candidate_capability_ids: list[str] = Field(default_factory=list)
    selected_strategy_id: str | None = None
    justification: str
    rejected_alternatives: list[dict[str, Any]] = Field(default_factory=list)
    score: float = 0.0
    criteria: dict[str, Any] = Field(default_factory=dict)
    reason_code: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    coverage: float = 0.0
    cost: float = 0.0
    latency: int = 0
    risk: str = "low"
    determinism: str = "unknown"
    policy_notes: list[str] = Field(default_factory=list)
    blocking_reason: str | None = None


CapabilityArbitrationDecision = CapabilityDecision


class ObservationTask(AIpinhoModel):
    observation_task_id: str = Field(default_factory=lambda: f"observation_task_{uuid4().hex}")
    goal_id: str
    contract_id: str | None = None
    artifact_id: str | None = None
    artifact_logical_path: str | None = None
    artifact_kind: str | None = None
    task_run_id: str | None = None
    strategy_id: str | None = None
    capability_id: str | None = None
    entity_ref: dict[str, Any] = Field(default_factory=dict)
    attribute_name: str
    canonical_key: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)
    status: ObservationTaskStatus = "PLANNED"
    execution_disposition: ObservationExecutionDisposition | None = None
    pre_defer_status: ObservationTaskStatus | None = None
    created_from: dict[str, Any] = Field(default_factory=dict)


class ObserverBinding(AIpinhoModel):
    binding_id: str = Field(default_factory=lambda: f"observer_binding_{uuid4().hex}")
    capability_id: str
    observer_id: str
    adapter_id: str | None = None
    observer_version: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    acquisition_method: str = "execute_observer"
    timeout_ms: int | None = None
    limitations: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class ObservationExecutionPolicy(AIpinhoModel):
    policy_id: str = Field(default_factory=lambda: f"observation_execution_policy_{uuid4().hex}")
    allow_execution: bool = True
    requires_approval: bool = False
    approved: bool = False
    timeout_ms: int = 30000
    min_confidence: float = 0.0
    max_risk_level: str = "medium"
    reason: str | None = None
    notes: list[str] = Field(default_factory=list)


class ObservationExecutionError(AIpinhoModel):
    error_id: str = Field(default_factory=lambda: f"observation_execution_error_{uuid4().hex}")
    code: ObservationExecutionErrorCode
    message: str
    capability_id: str | None = None
    observer_id: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ObservationExecutionTimelineEvent(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"observation_execution_event_{uuid4().hex}")
    event_type: str
    observation_task_id: str | None = None
    capability_id: str | None = None
    observer_id: str | None = None
    status: ObservationExecutionStatus | None = None
    reason_code: str | None = None
    message: str | None = None
    timestamp: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ObservationExecutionResult(AIpinhoModel):
    execution_id: str = Field(default_factory=lambda: f"observation_execution_{uuid4().hex}")
    observation_task_id: str
    goal_id: str | None = None
    strategy_id: str | None = None
    capability_id: str | None = None
    observer_id: str | None = None
    status: ObservationExecutionStatus
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    raw_ref: str | None = None
    evidence_set: "EvidenceSet" = Field(default_factory=lambda: EvidenceSet())
    errors: list[ObservationExecutionError] = Field(default_factory=list)
    timeline_events: list[ObservationExecutionTimelineEvent] = Field(default_factory=list)
    confidence: float = 0.0
    limitations: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    evidence_checkpoint_ref: dict[str, Any] = Field(default_factory=dict)
    evidence_checkpoint_digest: str | None = None
    evidence_record_count: int = 0
    evidence_record_refs: list[str] = Field(default_factory=list)
    evidence_canonical_keys: list[str] = Field(default_factory=list)
    evidence_checkpoint_bytes: int = 0
    evidence_inline: bool = True


class EvidenceRecord(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"evidence_{uuid4().hex}")
    source: str | None = None
    acquisition_method: str | None = None
    observer_id: str | None = None
    capability_id: str | None = None
    backend_id: str | None = None
    entity_ref: dict[str, Any] = Field(default_factory=dict)
    attribute_name: str | None = None
    canonical_key: str | None = None
    raw_ref: str | None = None
    normalized_value: Any | None = None
    semantic_type: str | None = None
    confidence: float = 0.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None
    ambiguity: float = 0.0
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_type: str | None = None
    candidate_id: str | None = None
    observation_id: str | None = None
    provenance_trace_id: str | None = None
    source_entity_ref: dict[str, Any] = Field(default_factory=dict)
    target_entity_ref: dict[str, Any] = Field(default_factory=dict)
    relation_family: str | None = None
    relation_kind_candidate: str | None = None
    signals: list[dict[str, Any]] = Field(default_factory=list)
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    truth_eligible: bool = False
    validation_required: bool = False


class EvidenceSet(AIpinhoModel):
    evidence_set_id: str = Field(default_factory=lambda: f"evidence_set_{uuid4().hex}")
    records: list[EvidenceRecord] = Field(default_factory=list)
    entity_refs: list[dict[str, Any]] = Field(default_factory=list)
    attribute_names: list[str] = Field(default_factory=list)
    canonical_keys: list[str] = Field(default_factory=list)
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    confidence_summary: dict[str, Any] = Field(default_factory=dict)
    checkpoint_refs: list[dict[str, Any]] = Field(default_factory=list)
    record_count: int = 0


class ObservationPlan(AIpinhoModel):
    observation_plan_id: str = Field(default_factory=lambda: f"observation_plan_{uuid4().hex}")
    contract_observation_plan_id: str | None = None
    candidate_set_id: str | None = None
    observation_goals: list[ObservationGoal] = Field(default_factory=list)
    observation_strategies: list[ObservationStrategy] = Field(default_factory=list)
    capability_matches: list[CapabilityMatch] = Field(default_factory=list)
    capability_decisions: list[CapabilityDecision] = Field(default_factory=list)
    observation_tasks: list[ObservationTask] = Field(default_factory=list)
    requirements: list[AttributeObservationRequirement] = Field(default_factory=list)
    semantic_gaps: list[dict[str, Any]] = Field(default_factory=list)


class AttributeObservation(AIpinhoModel):
    observation_id: str = Field(default_factory=lambda: f"attribute_observation_{uuid4().hex}")
    entity_id: str
    attribute_name: str
    canonical_key: str | None = None
    observed_value: Any | None = None
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    observer_id: str | None = None
    observer_version: str | None = None
    capability_id: str | None = None
    strategy_id: str | None = None
    acquisition_method: str | None = None
    observation_method: str | None = None
    execution_duration: float | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None
    ambiguity: float = 0.0
    observation_state: ObservationState = "missing"


class SemanticCoverage(AIpinhoModel):
    coverage_id: str = Field(default_factory=lambda: f"semantic_coverage_{uuid4().hex}")
    status: CoverageStatus = "not_applicable"
    coverage_ratio: float = 0.0
    observed_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    unsupported_fields: list[str] = Field(default_factory=list)
    ambiguous_fields: list[str] = Field(default_factory=list)
    candidate_entity_count: int = 0
    selected_entity_count: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    coverage_by_domain: dict[str, Any] = Field(default_factory=dict)
    semantic_gaps: list[dict[str, Any]] = Field(default_factory=list)


class SemanticCoverageReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"semantic_coverage_report_{uuid4().hex}")
    artifact_id: str | None = None
    contract_id: str | None = None
    artifact_logical_path: str | None = None
    artifact_kind: str | None = None
    task_run_id: str | None = None
    unbound_reason: str | None = None
    structural_coverage: float = 0.0
    entity_coverage: float = 0.0
    attribute_coverage: float = 0.0
    capability_coverage: float = 0.0
    evidence_coverage: float = 0.0
    semantic_confidence: float = 0.0
    missing_attributes: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    is_semantically_complete: bool = False


class KnowledgeRecord(AIpinhoModel):
    knowledge_id: str = Field(default_factory=lambda: f"knowledge_{uuid4().hex}")
    entity_ref: dict[str, Any] = Field(default_factory=dict)
    attribute_name: str | None = None
    canonical_key: str | None = None
    value: Any | None = None
    state: KnowledgeState = "UNKNOWN"
    fact_kind: str = "OBSERVED_FACT"
    source_kind: str = "observed"
    evidence_ids: list[str] = Field(default_factory=list)
    provenance_refs: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    observer_ids: list[str] = Field(default_factory=list)
    derivation_rule: str | None = None
    validation_eligibility: bool = False
    truth_eligibility: bool = False
    confidence: float = 0.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)


class SemanticAssertion(AIpinhoModel):
    assertion_id: str = Field(default_factory=lambda: f"semantic_assertion_{uuid4().hex}")
    assertion_kind: SemanticAssertionKind = "observation"
    state: KnowledgeState = "UNKNOWN"
    subject_ref: dict[str, Any] = Field(default_factory=dict)
    predicate: str
    object_value: Any | None = None
    fact_kind: str = "CANDIDATE_FACT"
    source_kind: str = "candidate"
    attribute_name: str | None = None
    canonical_key: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    knowledge_ids: list[str] = Field(default_factory=list)
    provenance_refs: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    derivation_rule: str | None = None
    validation_eligibility: bool = False
    confidence: float = 0.0
    truth_eligible: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class SemanticQualityQuestion(AIpinhoModel):
    question_id: str = Field(default_factory=lambda: f"semantic_quality_question_{uuid4().hex}")
    code: str
    dimension: str
    question: str
    status: SemanticQualityStatus
    attribute_name: str | None = None
    canonical_key: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    assertion_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    explanation: str | None = None
    recommendation: str | None = None


class SemanticSelfReview(AIpinhoModel):
    review_id: str = Field(default_factory=lambda: f"semantic_self_review_{uuid4().hex}")
    artifact_id: str | None = None
    contract_id: str | None = None
    artifact_logical_path: str | None = None
    task_run_id: str | None = None
    questions: list[SemanticQualityQuestion] = Field(default_factory=list)
    assertion_count: int = 0
    evidence_count: int = 0
    knowledge_count: int = 0
    findings: list[dict[str, Any]] = Field(default_factory=list)
    truth_readiness: CoverageStatus = "not_applicable"
    can_promote_to_validation: bool = False
    can_speaker_claim: bool = False
    reason_codes: list[str] = Field(default_factory=list)


class SemanticCoverage2(AIpinhoModel):
    coverage_id: str = Field(default_factory=lambda: f"semantic_coverage_2_{uuid4().hex}")
    structural_coverage: float = 0.0
    entity_coverage: float = 0.0
    attribute_coverage: float = 0.0
    capability_coverage: float = 0.0
    evidence_coverage: float = 0.0
    knowledge_coverage: float = 0.0
    semantic_coverage: float = 0.0
    truth_coverage: float = 0.0
    dimension_statuses: dict[str, CoverageStatus] = Field(default_factory=dict)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_truth_ready: bool = False


class ContractPerceptionResult(AIpinhoModel):
    contract_observation_plan: ContractObservationPlan
    candidate_entity_set: CandidateEntitySet
    specialization_hypotheses: list[SpecializationHypothesis] = Field(default_factory=list)
    observation_plan: ObservationPlan
    observation_execution_results: list[ObservationExecutionResult] = Field(default_factory=list)
    media_metadata_capability: dict[str, Any] = Field(default_factory=dict)
    relationship_goal: RelationshipGoal | None = None
    relationship_candidates: list[RelationshipCandidate] = Field(default_factory=list)
    relationship_evidence: list[RelationshipEvidence] = Field(default_factory=list)
    relationship_observations: list[RelationshipObservation] = Field(default_factory=list)
    relationship_provenance_traces: list[RelationshipProvenanceTrace] = Field(default_factory=list)
    relationship_summary: dict[str, Any] = Field(default_factory=dict)
    attribute_observations: list[AttributeObservation] = Field(default_factory=list)
    evidence_set: EvidenceSet = Field(default_factory=EvidenceSet)
    knowledge_records: list[KnowledgeRecord] = Field(default_factory=list)
    semantic_assertions: list[SemanticAssertion] = Field(default_factory=list)
    semantic_self_review: SemanticSelfReview = Field(default_factory=SemanticSelfReview)
    semantic_coverage: SemanticCoverage
    semantic_coverage_report: SemanticCoverageReport = Field(default_factory=SemanticCoverageReport)
    semantic_coverage_2: SemanticCoverage2 = Field(default_factory=SemanticCoverage2)
    compile_stage_trace: list[dict[str, Any]] = Field(default_factory=list)
    payload_metrics: dict[str, Any] = Field(default_factory=dict)
    compile_policy: dict[str, Any] = Field(default_factory=dict)
    internal_reason_code: str | None = None
