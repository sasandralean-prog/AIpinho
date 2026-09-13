from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.semantics.semantic_nway_topology import (
    SemanticJoinEvaluation,
    SemanticTopologyNeighborhood,
)


class SemanticNWayTopologyAuthorityService:
    """Hashes topology projections without changing underlying graph contracts."""

    def stable_sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def neighborhood_payload(
        self,
        value: SemanticTopologyNeighborhood,
    ) -> dict[str, Any]:
        return {
            "semantic_graph_id": value.semantic_graph_id,
            "semantic_graph_authority_sha256": (
                value.semantic_graph_authority_sha256
            ),
            "work_unit_id": value.work_unit_id,
            "incoming_edges": [
                item.model_dump(mode="json")
                for item in value.incoming_edges
            ],
            "outgoing_edges": [
                item.model_dump(mode="json")
                for item in value.outgoing_edges
            ],
            "fan_in_count": value.fan_in_count,
            "fan_out_count": value.fan_out_count,
            "required_incoming_edge_ids": list(
                value.required_incoming_edge_ids
            ),
            "optional_incoming_edge_ids": list(
                value.optional_incoming_edge_ids
            ),
            "outgoing_demand_ids": list(value.outgoing_demand_ids),
            "schema_version": value.schema_version,
        }

    def join_payload(
        self,
        value: SemanticJoinEvaluation,
    ) -> dict[str, Any]:
        return {
            "semantic_graph_id": value.semantic_graph_id,
            "semantic_graph_authority_sha256": (
                value.semantic_graph_authority_sha256
            ),
            "consumer_work_unit_id": value.consumer_work_unit_id,
            "required_edge_ids": list(value.required_edge_ids),
            "optional_edge_ids": list(value.optional_edge_ids),
            "compatibility_ids": list(value.compatibility_ids),
            "decision": value.decision,
            "admitted_edge_ids": list(value.admitted_edge_ids),
            "constrained_edge_ids": list(value.constrained_edge_ids),
            "blocked_edge_ids": list(value.blocked_edge_ids),
            "unresolved_edge_ids": list(value.unresolved_edge_ids),
            "optional_nonadmitted_edge_ids": list(
                value.optional_nonadmitted_edge_ids
            ),
            "effective_constraints": list(value.effective_constraints),
            "disclosures": list(value.disclosures),
            "reason_codes": list(value.reason_codes),
            "schema_version": value.schema_version,
        }

    def compute_neighborhood_sha256(
        self,
        value: SemanticTopologyNeighborhood,
    ) -> str:
        return self.stable_sha256(self.neighborhood_payload(value))

    def compute_join_sha256(
        self,
        value: SemanticJoinEvaluation,
    ) -> str:
        return self.stable_sha256(self.join_payload(value))

    def verify_neighborhood(
        self,
        value: SemanticTopologyNeighborhood,
    ) -> bool:
        return value.authority_sha256 == self.compute_neighborhood_sha256(
            value
        )

    def verify_join(self, value: SemanticJoinEvaluation) -> bool:
        return value.authority_sha256 == self.compute_join_sha256(value)
