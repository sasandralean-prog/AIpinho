from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.semantics.task_semantic_vocabulary import (
    TaskSemanticVocabularyBinding,
)


SemanticWorkUnitClassificationStatus = Literal["explicit", "interpreted", "unknown"]
SemanticExecutionGraphStatus = Literal["ready", "partial", "blocked"]
SemanticEdgeRelation = Literal[
    "semantic_dependency",
    "evidence_dependency",
    "validation_dependency",
    "context_dependency",
    "ordering_constraint",
]


class SemanticWorkUnitContract(AIpinhoModel):
    work_unit_id: str
    source_step_ids: list[str] = Field(default_factory=list)
    semantic_goal: str
    work_modes: list[str] = Field(default_factory=list)
    classification_status: SemanticWorkUnitClassificationStatus = "unknown"
    required_capabilities: list[str] = Field(default_factory=list)
    requested_effects: list[str] = Field(default_factory=list)
    prohibited_effects: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    source_inputs: dict[str, Any] = Field(default_factory=dict)
    required: bool = True
    contains_side_effect: bool = False
    vocabulary_binding: TaskSemanticVocabularyBinding


class SemanticDependencyEdge(AIpinhoModel):
    edge_id: str = Field(default_factory=lambda: f"semantic_edge_{uuid4().hex}")
    producer_work_unit_id: str
    consumer_work_unit_id: str
    relation: SemanticEdgeRelation
    required: bool = True
    source_refs: list[str] = Field(default_factory=list)


class SemanticExecutionGraph(AIpinhoModel):
    semantic_graph_id: str
    task_run_id: str
    task_id: str | None = None
    source_plan_id: str
    source_execution_id: str
    source_semantics_sha256: str
    vocabulary_binding: TaskSemanticVocabularyBinding
    work_units: list[SemanticWorkUnitContract] = Field(default_factory=list)
    edges: list[SemanticDependencyEdge] = Field(default_factory=list)
    status: SemanticExecutionGraphStatus
    reason_codes: list[str] = Field(default_factory=list)
    authority_sha256: str
    frozen_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "semantic_execution_graph.v1"


class SemanticWorkUnitCandidate(AIpinhoModel):
    unit_key: str
    source_step_ids: list[str] = Field(default_factory=list)
    semantic_goal: str
    work_modes: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    requested_effects: list[str] = Field(default_factory=list)
    prohibited_effects: list[str] = Field(default_factory=list)


class SemanticDependencyEdgeCandidate(AIpinhoModel):
    producer_unit_key: str
    consumer_unit_key: str
    relation: SemanticEdgeRelation
    required: bool = True


class SemanticWorkDecompositionCandidate(AIpinhoModel):
    work_units: list[SemanticWorkUnitCandidate] = Field(default_factory=list)
    edges: list[SemanticDependencyEdgeCandidate] = Field(default_factory=list)
    confidence: float
    rationale: str


class SemanticWorkDecompositionResult(AIpinhoModel):
    status: Literal["accepted", "insufficient_evidence", "not_required"]
    reason_code: str | None = None
    graph: SemanticExecutionGraph | None = None
    candidate: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
