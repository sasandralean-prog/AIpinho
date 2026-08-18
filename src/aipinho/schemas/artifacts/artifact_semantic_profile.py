from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ArtifactSemanticStatus = Literal["passed", "partial", "blocked", "not_applicable"]
ArtifactSemanticGapSeverity = Literal["info", "low", "medium", "high", "critical"]


class ArtifactSemanticGap(AIpinhoModel):
    gap_id: str = Field(default_factory=lambda: f"artifact_semantic_gap_{uuid4().hex}")
    gap_type: str
    reason_code: str | None = None
    perception_domain: str | None = None
    severity: ArtifactSemanticGapSeverity = "medium"
    expected: Any | None = None
    observed: Any | None = None
    confidence: float = 1.0
    repair_hint: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class SemanticComparison(AIpinhoModel):
    matches: list[str] = Field(default_factory=list)
    missing_parts: list[str] = Field(default_factory=list)
    unexpected_parts: list[str] = Field(default_factory=list)
    semantic_distance: float = 0.0
    confidence: float = 1.0


class ArtifactSemanticProfile(AIpinhoModel):
    profile_id: str = Field(default_factory=lambda: f"artifact_semantic_profile_{uuid4().hex}")
    artifact_id: str | None = None
    artifact_type: str | None = None
    artifact_path: str | None = None
    artifact_logical_path: str | None = None
    artifact_kind: str | None = None
    task_run_id: str | None = None
    content_type: str | None = None
    declared_contract: dict[str, Any] = Field(default_factory=dict)
    expected_kind: str | None = None
    expected_schema: list[str] = Field(default_factory=list)
    canonical_schema: list[str] = Field(default_factory=list)
    attribute_contracts: list[dict[str, Any]] = Field(default_factory=list)
    expected_behavior: dict[str, Any] = Field(default_factory=dict)
    expected_semantics: dict[str, Any] = Field(default_factory=dict)
    expected_evidence: list[str] = Field(default_factory=list)
    expected_relationships: list[dict[str, Any]] = Field(default_factory=list)
    expected_entities: list[dict[str, Any]] = Field(default_factory=list)
    expected_cardinality: dict[str, Any] = Field(default_factory=dict)
    observed_kind: str | None = None
    observed_schema: list[str] = Field(default_factory=list)
    observed_behavior: dict[str, Any] = Field(default_factory=dict)
    observed_semantics: dict[str, Any] = Field(default_factory=dict)
    observed_evidence: list[str] = Field(default_factory=list)
    observed_entities: list[dict[str, Any]] = Field(default_factory=list)
    bound_attribute_observations: list[dict[str, Any]] = Field(default_factory=list)
    bound_relationship_observations: list[dict[str, Any]] = Field(default_factory=list)
    relationship_provenance_traces: list[dict[str, Any]] = Field(default_factory=list)
    relationship_evidence_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_candidates_by_artifact: dict[str, int] = Field(default_factory=dict)
    relationship_confidence_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_conflict_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_negative_evidence_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_binding_quality: dict[str, Any] = Field(default_factory=dict)
    relationship_rendered_fields: dict[str, Any] = Field(default_factory=dict)
    relationship_rendering_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_validation_results: list[dict[str, Any]] = Field(default_factory=list)
    relationship_validation_summary: dict[str, Any] = Field(default_factory=dict)
    validation_ready_count: int = 0
    validated_relationship_count: int = 0
    blocked_relationship_count: int = 0
    conflicted_relationship_count: int = 0
    truth_eligible_relationship_count: int = 0
    relationship_limitations: list[str] = Field(default_factory=list)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    schema_coverage: dict[str, Any] = Field(default_factory=dict)
    perception: dict[str, Any] = Field(default_factory=dict)
    semantic_gaps: list[ArtifactSemanticGap] = Field(default_factory=list)
    contract_gaps: list[ArtifactSemanticGap] = Field(default_factory=list)
    consistency_gaps: list[ArtifactSemanticGap] = Field(default_factory=list)
    comparison: SemanticComparison = Field(default_factory=SemanticComparison)
    confidence: float = 1.0
    completeness_score: float = 0.0
    structural_status: ArtifactSemanticStatus = "not_applicable"
    material_status: ArtifactSemanticStatus = "not_applicable"
    semantic_status: ArtifactSemanticStatus = "not_applicable"
    contract_status: ArtifactSemanticStatus = "not_applicable"
    consistency_status: ArtifactSemanticStatus = "not_applicable"

    @property
    def passed(self) -> bool:
        statuses = {
            self.structural_status,
            self.material_status,
            self.semantic_status,
            self.contract_status,
            self.consistency_status,
        }
        return "blocked" not in statuses and self.semantic_status == "passed"
