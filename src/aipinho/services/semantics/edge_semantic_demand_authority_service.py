from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.semantics.edge_semantic_demand import EdgeSemanticDemand


class EdgeSemanticDemandAuthorityService:
    """Computes and verifies canonical edge-local semantic demand authority."""

    def stable_sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def authority_payload(self, demand: EdgeSemanticDemand) -> dict[str, Any]:
        return {
            "edge_id": demand.edge_id,
            "semantic_graph_id": demand.semantic_graph_id,
            "semantic_graph_authority_sha256": (
                demand.semantic_graph_authority_sha256
            ),
            "producer_work_unit_id": demand.producer_work_unit_id,
            "consumer_work_unit_id": demand.consumer_work_unit_id,
            "vocabulary_binding": demand.vocabulary_binding.model_dump(mode="json"),
            "status": demand.status,
            "consumer_required_capabilities": list(
                demand.consumer_required_capabilities
            ),
            "required_downstream_uses": list(demand.required_downstream_uses),
            "required_use_safety": dict(demand.required_use_safety),
            "required_semantic_properties": dict(
                demand.required_semantic_properties
            ),
            "required_evidence_domains": list(
                demand.required_evidence_domains
            ),
            "required_upstream_effects": list(
                demand.required_upstream_effects
            ),
            "prohibited_upstream_effects": list(
                demand.prohibited_upstream_effects
            ),
            "evidence_required": demand.evidence_required,
            "base_constraints": list(demand.base_constraints),
            "risk_constraints": list(demand.risk_constraints),
            "source_consumer_step_ids": list(
                demand.source_consumer_step_ids
            ),
            "source_refs": list(demand.source_refs),
            "reason_codes": list(demand.reason_codes),
            "schema_version": demand.schema_version,
        }

    def compute_authority_sha256(self, demand: EdgeSemanticDemand) -> str:
        return self.stable_sha256(self.authority_payload(demand))

    def verify(self, demand: EdgeSemanticDemand) -> bool:
        return demand.authority_sha256 == self.compute_authority_sha256(demand)
