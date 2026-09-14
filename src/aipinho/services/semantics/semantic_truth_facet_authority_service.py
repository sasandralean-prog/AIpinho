from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.semantics.semantic_truth_facet import SemanticTruthFacet


class SemanticTruthFacetAuthorityService:
    """Hashes semantic truth facets without changing underlying graph contracts."""

    def stable_sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def authority_payload(self, facet: SemanticTruthFacet) -> dict[str, Any]:
        return {
            "status": facet.status,
            "safe_to_report_success": facet.safe_to_report_success,
            "semantic_graph_id": facet.semantic_graph_id,
            "semantic_graph_authority_sha256": (
                facet.semantic_graph_authority_sha256
            ),
            "active_revision_id": facet.active_revision_id,
            "required_edge_ids": list(facet.required_edge_ids),
            "admitted_edge_ids": list(facet.admitted_edge_ids),
            "constrained_edge_ids": list(facet.constrained_edge_ids),
            "blocked_edge_ids": list(facet.blocked_edge_ids),
            "unresolved_edge_ids": list(facet.unresolved_edge_ids),
            "partial_demand_edge_ids": list(
                facet.partial_demand_edge_ids
            ),
            "required_join_consumer_ids": list(
                facet.required_join_consumer_ids
            ),
            "constrained_join_consumer_ids": list(
                facet.constrained_join_consumer_ids
            ),
            "blocked_join_consumer_ids": list(
                facet.blocked_join_consumer_ids
            ),
            "unresolved_join_consumer_ids": list(
                facet.unresolved_join_consumer_ids
            ),
            "disclosures": list(facet.disclosures),
            "invalid_authority_refs": list(
                facet.invalid_authority_refs
            ),
            "reason_codes": list(facet.reason_codes),
            "schema_version": facet.schema_version,
        }

    def compute_authority_sha256(self, facet: SemanticTruthFacet) -> str:
        return self.stable_sha256(self.authority_payload(facet))

    def verify(self, facet: SemanticTruthFacet) -> bool:
        return (
            facet.authority_sha256
            == self.compute_authority_sha256(facet)
        )
