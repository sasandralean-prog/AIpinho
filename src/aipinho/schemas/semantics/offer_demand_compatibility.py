from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


CompatibilityDecision = Literal[
    "admitted",
    "admitted_with_constraints",
    "blocked",
    "insufficient_evidence",
]


class OfferDemandCompatibility(AIpinhoModel):
    compatibility_id: str
    edge_id: str
    semantic_graph_id: str
    semantic_graph_authority_sha256: str
    producer_work_unit_id: str
    consumer_work_unit_id: str
    offer_id: str
    offer_authority_sha256: str
    demand_id: str
    demand_authority_sha256: str
    decision: CompatibilityDecision
    satisfied_dimensions: list[str] = Field(default_factory=list)
    constrained_dimensions: list[str] = Field(default_factory=list)
    blocked_dimensions: list[str] = Field(default_factory=list)
    unknown_dimensions: list[str] = Field(default_factory=list)
    effective_constraints: list[str] = Field(default_factory=list)
    disclosures: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    authority_sha256: str
    evaluated_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "offer_demand_compatibility.v1"


class OfferDemandCompatibilityEvaluation(AIpinhoModel):
    evaluation_id: str = Field(
        default_factory=lambda: f"offer_demand_compatibility_eval_{uuid4().hex}"
    )
    status: Literal["evaluated", "insufficient_contract_evidence", "blocked"]
    compatibility: OfferDemandCompatibility | None = None
    reason_codes: list[str] = Field(default_factory=list)
    evaluated_at: str = Field(default_factory=utc_now_iso)
