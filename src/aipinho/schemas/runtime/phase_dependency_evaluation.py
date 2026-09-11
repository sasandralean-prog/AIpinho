from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


DependencyAdmissionDecision = Literal[
    "ADMITTED",
    "ADMITTED_WITH_CONSTRAINTS",
    "BLOCKED",
    "NOT_EVALUATED",
    "INSUFFICIENT_EVIDENCE",
]
SemanticDemandCompilationStatus = Literal["compiled", "insufficient_contract_evidence", "blocked"]
LimitationCompatibility = Literal[
    "COMPATIBLE",
    "COMPATIBLE_WITH_CONSTRAINT",
    "INCOMPATIBLE",
    "NOT_APPLICABLE",
    "UNKNOWN",
]


class RequirementProvenance(AIpinhoModel):
    requirement: str
    source_kind: Literal[
        "canonical_execution_plan",
        "canonical_execution_step",
        "semantic_intent_graph",
        "policy_snapshot",
        "system_invariant",
    ]
    source_ref: str
    source_field: str
    source_sha256: str


class DownstreamPhaseRequirements(AIpinhoModel):
    contract_id: str
    contract_version: str = "1"
    consumer_phase_id: str
    operation_type: str
    authority_source: Literal[
        "compiled_task_semantics",
        "compiled_task_semantics_with_system_invariants",
        "trusted_registry",
        "workflow_contract",
        "system_invariant",
    ] = "trusted_registry"
    allowed_dependency_statuses: list[str] = Field(default_factory=lambda: ["satisfied"])
    required_downstream_uses: list[str] = Field(default_factory=list)
    required_use_safety: dict[str, list[Any]] = Field(default_factory=dict)
    required_semantic_properties: dict[str, list[Any]] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)
    limitation_compatibility: dict[str, LimitationCompatibility] = Field(default_factory=dict)
    base_constraints: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    prohibited_effects: list[str] = Field(default_factory=list)
    evidence_required: bool = True
    authorization_ttl_seconds: int = 900
    source_plan_id: str | None = None
    source_execution_id: str | None = None
    source_semantics_sha256: str | None = None
    frozen_at: str | None = None
    requirement_provenance: list[RequirementProvenance] = Field(default_factory=list)


class PhaseSemanticDemandCompilation(AIpinhoModel):
    compilation_id: str = Field(default_factory=lambda: f"phase_semantic_demand_{uuid4().hex}")
    status: SemanticDemandCompilationStatus
    consumer_phase_id: str
    consumer_operation_type: str
    source_plan_id: str | None = None
    source_execution_id: str | None = None
    source_semantics_sha256: str | None = None
    requirements: DownstreamPhaseRequirements | None = None
    reason_codes: list[str] = Field(default_factory=list)
    compiled_at: str = Field(default_factory=utc_now_iso)
    frozen_before_admission: bool = True


class PhaseDependencySnapshot(AIpinhoModel):
    dependency_id: str
    producer_task_run_id: str
    producer_operation_id: str | None = None
    producer_phase_id: str
    upstream_result_ref: str
    dependency_status: str
    evidence_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)
    missing_truth: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    allowed_downstream_uses: list[str] = Field(default_factory=list)
    forbidden_downstream_uses: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    use_safety: dict[str, Any] = Field(default_factory=dict)
    semantic_properties: dict[str, Any] = Field(default_factory=dict)


class DependencyRequirementCheck(AIpinhoModel):
    requirement: str
    expected: list[Any] = Field(default_factory=list)
    observed: Any = None
    status: Literal["satisfied", "blocked", "unknown"]
    reason_code: str | None = None


class LimitationAssessment(AIpinhoModel):
    limitation: str
    impact: LimitationCompatibility
    source: Literal["downstream_contract", "upstream_disclosure", "unclassified"]
    constraints: list[str] = Field(default_factory=list)


class PhaseDependencyEvaluation(AIpinhoModel):
    evaluation_id: str = Field(default_factory=lambda: f"phase_dependency_evaluation_{uuid4().hex}")
    dependency_id: str
    producer_task_run_id: str
    producer_operation_id: str | None = None
    consumer_task_run_id: str
    consumer_operation_id: str
    consumer_operation_type: str
    producer_phase_id: str
    consumer_phase_id: str
    upstream_result_ref: str
    downstream_contract_id: str
    downstream_contract_version: str
    requirements_sha256: str
    dependency_status: str
    evaluation_status: Literal["completed", "incomplete"]
    decision: DependencyAdmissionDecision
    reason_codes: list[str] = Field(default_factory=list)
    requirement_checks: list[DependencyRequirementCheck] = Field(default_factory=list)
    limitation_assessments: list[LimitationAssessment] = Field(default_factory=list)
    missing_truth: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    evaluated_at: str = Field(default_factory=utc_now_iso)
    expires_at: str
    authority_sha256: str = ""


class PhaseDependencyAdmission(AIpinhoModel):
    admission_id: str = Field(default_factory=lambda: f"phase_dependency_admission_{uuid4().hex}")
    evaluation_id: str
    dependency_id: str
    producer_task_run_id: str
    producer_operation_id: str | None = None
    consumer_task_run_id: str
    consumer_operation_id: str
    consumer_operation_type: str
    producer_phase_id: str
    consumer_phase_id: str
    downstream_contract_id: str
    requirements_sha256: str
    evaluation_authority_sha256: str
    authorized: bool
    decision: DependencyAdmissionDecision
    reason_code: str
    missing_truth: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    admitted_at: str = Field(default_factory=utc_now_iso)
    expires_at: str
    authority_sha256: str = ""
