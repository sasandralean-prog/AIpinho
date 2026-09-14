from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


SemanticTruthFacetStatus = Literal[
    "not_applicable",
    "ready",
    "constrained",
    "blocked",
    "insufficient_evidence",
]


class SemanticTruthFacet(AIpinhoModel):
    facet_id: str
    status: SemanticTruthFacetStatus
    safe_to_report_success: bool = False
    semantic_graph_id: str | None = None
    semantic_graph_authority_sha256: str | None = None
    active_revision_id: str | None = None
    required_edge_ids: list[str] = Field(default_factory=list)
    admitted_edge_ids: list[str] = Field(default_factory=list)
    constrained_edge_ids: list[str] = Field(default_factory=list)
    blocked_edge_ids: list[str] = Field(default_factory=list)
    unresolved_edge_ids: list[str] = Field(default_factory=list)
    partial_demand_edge_ids: list[str] = Field(default_factory=list)
    required_join_consumer_ids: list[str] = Field(default_factory=list)
    constrained_join_consumer_ids: list[str] = Field(default_factory=list)
    blocked_join_consumer_ids: list[str] = Field(default_factory=list)
    unresolved_join_consumer_ids: list[str] = Field(default_factory=list)
    disclosures: list[str] = Field(default_factory=list)
    invalid_authority_refs: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    authority_sha256: str
    evaluated_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "semantic_truth_facet.v1"
