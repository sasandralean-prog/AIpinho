from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.semantics.semantic_execution_graph import (
    SemanticEdgeRelation,
    SemanticExecutionGraph,
    SemanticWorkUnitClassificationStatus,
)


class SemanticGraphRevisionWorkUnitAddition(AIpinhoModel):
    addition_key: str
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


class SemanticGraphRevisionEdgeAddition(AIpinhoModel):
    addition_key: str
    producer_ref: str
    consumer_ref: str
    relation: SemanticEdgeRelation
    required: bool = True
    source_refs: list[str] = Field(default_factory=list)


class SemanticGraphRevisionProposal(AIpinhoModel):
    proposal_id: str = Field(
        default_factory=lambda: f"semantic_graph_revision_proposal_{uuid4().hex}"
    )
    parent_graph_id: str
    parent_graph_authority_sha256: str
    parent_revision_id: str | None = None
    revision_number: int
    reason: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    add_work_units: list[SemanticGraphRevisionWorkUnitAddition] = Field(
        default_factory=list
    )
    add_edges: list[SemanticGraphRevisionEdgeAddition] = Field(
        default_factory=list
    )
    remove_edge_ids: list[str] = Field(default_factory=list)
    remove_work_unit_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "semantic_graph_revision_proposal.v1"


class SemanticGraphRevision(AIpinhoModel):
    revision_id: str
    revision_number: int
    parent_revision_id: str | None = None
    parent_graph_id: str
    parent_graph_authority_sha256: str
    child_graph_id: str
    child_graph_authority_sha256: str
    revision_intent_sha256: str
    reason: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    added_work_unit_ids: list[str] = Field(default_factory=list)
    added_edge_ids: list[str] = Field(default_factory=list)
    removed_work_unit_ids: list[str] = Field(default_factory=list)
    removed_edge_ids: list[str] = Field(default_factory=list)
    edges_requiring_demand_recompile: list[str] = Field(default_factory=list)
    authority_sha256: str
    applied_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "semantic_graph_revision.v1"


class SemanticGraphRevisionApplication(AIpinhoModel):
    application_id: str = Field(
        default_factory=lambda: f"semantic_graph_revision_application_{uuid4().hex}"
    )
    status: Literal["applied", "blocked", "insufficient_contract_evidence"]
    revision: SemanticGraphRevision | None = None
    child_graph: SemanticExecutionGraph | None = None
    reason_codes: list[str] = Field(default_factory=list)
    applied_at: str = Field(default_factory=utc_now_iso)
