from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


NWayJoinDecision = Literal[
    "admitted",
    "admitted_with_constraints",
    "blocked",
    "insufficient_evidence",
]


class SemanticTopologyEdgeState(AIpinhoModel):
    edge_id: str
    producer_work_unit_id: str
    consumer_work_unit_id: str
    required: bool
    demand_id: str | None = None
    demand_authority_sha256: str | None = None
    offer_id: str | None = None
    offer_authority_sha256: str | None = None
    compatibility_id: str | None = None
    compatibility_authority_sha256: str | None = None
    compatibility_decision: str | None = None


class SemanticTopologyNeighborhood(AIpinhoModel):
    neighborhood_id: str
    semantic_graph_id: str
    semantic_graph_authority_sha256: str
    work_unit_id: str
    incoming_edges: list[SemanticTopologyEdgeState] = Field(default_factory=list)
    outgoing_edges: list[SemanticTopologyEdgeState] = Field(default_factory=list)
    fan_in_count: int = 0
    fan_out_count: int = 0
    required_incoming_edge_ids: list[str] = Field(default_factory=list)
    optional_incoming_edge_ids: list[str] = Field(default_factory=list)
    outgoing_demand_ids: list[str] = Field(default_factory=list)
    authority_sha256: str
    projected_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "semantic_topology_neighborhood.v1"


class SemanticJoinEvaluation(AIpinhoModel):
    join_id: str
    semantic_graph_id: str
    semantic_graph_authority_sha256: str
    consumer_work_unit_id: str
    required_edge_ids: list[str] = Field(default_factory=list)
    optional_edge_ids: list[str] = Field(default_factory=list)
    compatibility_ids: list[str] = Field(default_factory=list)
    decision: NWayJoinDecision
    admitted_edge_ids: list[str] = Field(default_factory=list)
    constrained_edge_ids: list[str] = Field(default_factory=list)
    blocked_edge_ids: list[str] = Field(default_factory=list)
    unresolved_edge_ids: list[str] = Field(default_factory=list)
    optional_nonadmitted_edge_ids: list[str] = Field(default_factory=list)
    effective_constraints: list[str] = Field(default_factory=list)
    disclosures: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    authority_sha256: str
    evaluated_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "semantic_join_evaluation.v1"


class SemanticJoinEvaluationResult(AIpinhoModel):
    evaluation_id: str = Field(
        default_factory=lambda: f"semantic_join_eval_{uuid4().hex}"
    )
    status: Literal["evaluated", "not_applicable", "insufficient_contract_evidence"]
    join: SemanticJoinEvaluation | None = None
    reason_codes: list[str] = Field(default_factory=list)
