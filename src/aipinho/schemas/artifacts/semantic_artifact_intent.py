from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactIntentPlan(AIpinhoModel):
    plan_id: str = Field(default_factory=lambda: f"artifact_intent_plan_{uuid4().hex}")
    artifact_kind: str
    semantic_domain: str
    target_subject: str | None = None
    source_root_roles_required: list[str] = Field(default_factory=list)
    required_entity_types: list[str] = Field(default_factory=list)
    required_entity_roles: list[str] = Field(default_factory=list)
    required_attributes: list[str] = Field(default_factory=list)
    optional_attributes: list[str] = Field(default_factory=list)
    required_relationship_families: list[str] = Field(default_factory=list)
    required_evidence_types: list[str] = Field(default_factory=list)
    allowed_absence_states: list[str] = Field(default_factory=list)
    minimum_semantic_rows: int = 1
    partial_allowed: bool = True
    block_reason_if_missing: str = "ARTIFACT_SEMANTIC_BINDING_INSUFFICIENT"
    resolution_confidence: float = 0.0
    resolution_sources: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticEntitySelectionResult(AIpinhoModel):
    selection_id: str = Field(default_factory=lambda: f"semantic_entity_selection_{uuid4().hex}")
    artifact_intent_plan_id: str
    status: str
    reason_code: str | None = None
    expected_rows: int = 0
    selected_rows: int = 0
    bound_rows: int = 0
    evidence_ref_count: int = 0
    root_roles_seen: dict[str, int] = Field(default_factory=dict)
    root_roles_selected: dict[str, int] = Field(default_factory=dict)
    selected_entity_ids: list[str] = Field(default_factory=list)
    rejected_count: int = 0
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    semantic_gaps: list[dict[str, Any]] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] = Field(default_factory=dict)
