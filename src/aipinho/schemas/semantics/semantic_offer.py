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


SemanticOfferStatus = Literal["complete", "partial", "unknown"]


class ObservedWorkUnitSemanticOutcome(AIpinhoModel):
    producer_work_unit_id: str
    source_step_ids: list[str] = Field(default_factory=list)
    result_status: str
    result_ref: str
    observed_use_safety: dict[str, SemanticScalar] = Field(default_factory=dict)
    observed_semantic_properties: dict[str, SemanticScalar] = Field(
        default_factory=dict
    )
    allowed_downstream_uses: list[str] = Field(default_factory=list)
    evidence_domains: list[str] = Field(default_factory=list)
    observed_effects: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    missing_truth: list[str] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class SemanticOffer(AIpinhoModel):
    offer_id: str
    semantic_graph_id: str
    semantic_graph_authority_sha256: str
    producer_work_unit_id: str
    vocabulary_binding: TaskSemanticVocabularyBinding
    status: SemanticOfferStatus
    result_status: str
    result_ref: str
    source_step_ids: list[str] = Field(default_factory=list)
    use_safety: dict[str, SemanticScalar] = Field(default_factory=dict)
    semantic_properties: dict[str, SemanticScalar] = Field(default_factory=dict)
    allowed_downstream_uses: list[str] = Field(default_factory=list)
    evidence_domains: list[str] = Field(default_factory=list)
    observed_effects: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    missing_truth: list[str] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    source_provenance: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    authority_sha256: str
    frozen_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "semantic_offer.v1"


class SemanticOfferCompilation(AIpinhoModel):
    compilation_id: str = Field(
        default_factory=lambda: f"semantic_offer_compilation_{uuid4().hex}"
    )
    status: Literal["compiled", "insufficient_evidence", "blocked"]
    producer_work_unit_id: str | None = None
    offer: SemanticOffer | None = None
    reason_codes: list[str] = Field(default_factory=list)
    compiled_at: str = Field(default_factory=utc_now_iso)
