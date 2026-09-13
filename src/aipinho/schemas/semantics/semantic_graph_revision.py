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
from aipinho.schemas.semantics.edge_semantic_demand import EdgeSemanticDemand
from aipinho.schemas.semantics.semantic_offer import SemanticOffer
from aipinho.schemas.semantics.offer_demand_compatibility import (
    OfferDemandCompatibility,
)
from aipinho.schemas.semantics.semantic_nway_topology import (
    SemanticJoinEvaluation,
    SemanticTopologyNeighborhood,
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


class SemanticGraphHistorySnapshot(AIpinhoModel):
    snapshot_id: str
    revision_id: str | None = None
    graph: SemanticExecutionGraph
    edge_semantic_demands: list[EdgeSemanticDemand] = Field(default_factory=list)
    semantic_offers: list[SemanticOffer] = Field(default_factory=list)
    offer_demand_compatibilities: list[OfferDemandCompatibility] = Field(
        default_factory=list
    )
    semantic_topology_neighborhoods: list[SemanticTopologyNeighborhood] = Field(
        default_factory=list
    )
    semantic_join_evaluations: list[SemanticJoinEvaluation] = Field(
        default_factory=list
    )
    authority_sha256: str
    archived_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "semantic_graph_history_snapshot.v1"


class SemanticGraphActivationResult(AIpinhoModel):
    activation_id: str = Field(
        default_factory=lambda: f"semantic_graph_activation_{uuid4().hex}"
    )
    status: Literal["activated", "blocked", "insufficient_contract_evidence"]
    active_revision_id: str | None = None
    active_graph_id: str | None = None
    active_graph_authority_sha256: str | None = None
    snapshot_id: str | None = None
    demands_recompiled: int = 0
    partial_demands: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    activated_at: str = Field(default_factory=utc_now_iso)
