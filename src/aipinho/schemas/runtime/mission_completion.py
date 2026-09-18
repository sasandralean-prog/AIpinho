from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class MissionCompletionSnapshot(AIpinhoModel):
    mission_id: str
    status: Literal["ready", "missing", "invalid"]
    reason_codes: list[str] = Field(default_factory=list)
    source_prompt_sha256: str | None = None
    strategy: str | None = None
    semantic_context: dict[str, object] = Field(default_factory=dict)
    completion_requirements: list[str] = Field(default_factory=list)
    validation_requirements: list[str] = Field(default_factory=list)
    allow_limited_completion: bool = False
    task_run_ids: list[str] = Field(default_factory=list)
    terminal_task_run_ids: list[str] = Field(default_factory=list)
    phase_outcome_run_ids: list[str] = Field(default_factory=list)
    phase_outcome_authority_sha256s: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    contract_authority_sha256s: list[str] = Field(default_factory=list)
    contract_revisions: list[int] = Field(default_factory=list)
    authority_sha256: str
    projected_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "mission_completion_snapshot.v1"


class MissionCompletionRequirementEvaluation(AIpinhoModel):
    requirement: str
    requirement_kind: Literal["completion", "validation"]
    status: Literal[
        "satisfied",
        "satisfied_with_limitations",
        "unsatisfied",
        "blocked",
    ]
    evidence_refs: list[str] = Field(default_factory=list)
    producer_task_run_ids: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class MissionCompletionFacet(AIpinhoModel):
    mission_id: str
    snapshot_authority_sha256: str
    status: Literal[
        "not_applicable",
        "ready",
        "constrained",
        "insufficient_evidence",
        "blocked",
    ]
    safe_to_report_success: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    disclosures: list[str] = Field(default_factory=list)
    completion_evaluations: list[
        MissionCompletionRequirementEvaluation
    ] = Field(default_factory=list)
    validation_evaluations: list[
        MissionCompletionRequirementEvaluation
    ] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    producer_task_run_ids: list[str] = Field(default_factory=list)
    authority_sha256: str
    schema_version: str = "mission_completion_facet.v1"


class MissionCompletionEvidenceItem(AIpinhoModel):
    evidence_ref: str
    producer_task_run_id: str
    phase_id: str
    phase_outcome_authority_sha256: str
    runtime_status: str
    result_status: str
    runtime_truth_status: str | None = None
    runtime_truth_safe_to_report_success: bool | None = None
    phase_dependency_status: str | None = None
    reason_code: str | None = None
    limitations: list[str] = Field(default_factory=list)
    missing_truth: list[str] = Field(default_factory=list)
    use_safety: dict[str, object] = Field(default_factory=dict)
    semantic_properties: dict[str, object] = Field(default_factory=dict)
    artifact_descriptors: list[dict[str, object]] = Field(default_factory=list)


class MissionCompletionEvidenceCatalog(AIpinhoModel):
    mission_id: str
    snapshot_authority_sha256: str
    items: list[MissionCompletionEvidenceItem] = Field(default_factory=list)
    authority_sha256: str
    schema_version: str = "mission_completion_evidence_catalog.v1"


class MissionCompletionBindingCandidate(AIpinhoModel):
    requirement: str
    requirement_kind: Literal["completion", "validation"]
    semantic_relation: Literal["supports", "does_not_support", "ambiguous"]
    evidence_refs: list[str] = Field(default_factory=list)
    producer_task_run_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""


class MissionCompletionBindingProposal(AIpinhoModel):
    mission_id: str
    snapshot_authority_sha256: str
    catalog_authority_sha256: str
    status: Literal["candidate", "unavailable", "invalid"]
    reason_code: str
    bindings: list[MissionCompletionBindingCandidate] = Field(default_factory=list)
    provenance: dict[str, object] = Field(default_factory=dict)
    proposal_sha256: str
    schema_version: str = "mission_completion_binding_proposal.v1"


class MissionCompletionBindingCompilation(AIpinhoModel):
    mission_id: str
    snapshot_authority_sha256: str
    catalog_authority_sha256: str
    proposal_sha256: str
    status: Literal["compiled", "blocked"]
    reason_codes: list[str] = Field(default_factory=list)
    evaluations: list[MissionCompletionRequirementEvaluation] = Field(default_factory=list)
    schema_version: str = "mission_completion_binding_compilation.v1"


class MissionCompletionResolution(AIpinhoModel):
    mission_id: str
    status: Literal[
        "not_applicable",
        "ready",
        "constrained",
        "insufficient_evidence",
        "blocked",
        "unavailable",
    ]
    reason_codes: list[str] = Field(default_factory=list)
    snapshot_authority_sha256: str | None = None
    catalog_authority_sha256: str | None = None
    proposal_sha256: str | None = None
    proposal_source: Literal["generated", "persisted", "none"] = "none"
    compilation_status: str | None = None
    facet: MissionCompletionFacet | None = None
    schema_version: str = "mission_completion_resolution.v1"
