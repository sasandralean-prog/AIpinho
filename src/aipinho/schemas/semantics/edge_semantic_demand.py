from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.semantics.task_semantic_vocabulary import (
    SemanticScalar,
    TaskSemanticVocabularyBinding,
)


EdgeSemanticDemandStatus = Literal["ready", "partial"]


class EdgeSemanticDemand(AIpinhoModel):
    demand_id: str
    edge_id: str
    semantic_graph_id: str
    semantic_graph_authority_sha256: str
    producer_work_unit_id: str
    consumer_work_unit_id: str
    vocabulary_binding: TaskSemanticVocabularyBinding
    status: EdgeSemanticDemandStatus
    consumer_required_capabilities: list[str] = Field(default_factory=list)
    required_downstream_uses: list[str] = Field(default_factory=list)
    required_use_safety: dict[str, list[SemanticScalar]] = Field(
        default_factory=dict
    )
    required_semantic_properties: dict[str, list[SemanticScalar]] = Field(
        default_factory=dict
    )
    required_evidence_domains: list[str] = Field(default_factory=list)
    required_upstream_effects: list[str] = Field(default_factory=list)
    prohibited_upstream_effects: list[str] = Field(default_factory=list)
    evidence_required: bool = True
    base_constraints: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    source_consumer_step_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    authority_sha256: str
    frozen_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "edge_semantic_demand.v1"


class EdgeSemanticDemandCompilation(AIpinhoModel):
    compilation_id: str = Field(
        default_factory=lambda: f"edge_semantic_demand_compilation_{uuid4().hex}"
    )
    status: Literal[
        "compiled",
        "insufficient_contract_evidence",
        "blocked",
    ]
    edge_id: str | None = None
    demand: EdgeSemanticDemand | None = None
    reason_codes: list[str] = Field(default_factory=list)
    semantic_interpretation: dict[str, Any] = Field(default_factory=dict)
    compiled_at: str = Field(default_factory=utc_now_iso)
    frozen_before_compatibility: bool = True


class EdgeSemanticDemandCandidate(AIpinhoModel):
    required_downstream_uses: list[str] = Field(default_factory=list)
    required_use_safety: dict[str, list[SemanticScalar]] = Field(
        default_factory=dict
    )
    required_semantic_properties: dict[str, list[SemanticScalar]] = Field(
        default_factory=dict
    )
    required_evidence_domains: list[str] = Field(default_factory=list)
    required_upstream_effects: list[str] = Field(default_factory=list)
    prohibited_upstream_effects: list[str] = Field(default_factory=list)
    evidence_required: bool = True
    base_constraints: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    confidence: float
    rationale: str
