from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.semantics.offer_demand_compatibility import (
    OfferDemandCompatibility,
)


class OfferDemandCompatibilityAuthorityService:
    """Hashes immutable compatibility decisions over exact Offer/Demand inputs."""

    def stable_sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def authority_payload(
        self,
        compatibility: OfferDemandCompatibility,
    ) -> dict[str, Any]:
        return {
            "edge_id": compatibility.edge_id,
            "semantic_graph_id": compatibility.semantic_graph_id,
            "semantic_graph_authority_sha256": (
                compatibility.semantic_graph_authority_sha256
            ),
            "producer_work_unit_id": compatibility.producer_work_unit_id,
            "consumer_work_unit_id": compatibility.consumer_work_unit_id,
            "offer_id": compatibility.offer_id,
            "offer_authority_sha256": compatibility.offer_authority_sha256,
            "demand_id": compatibility.demand_id,
            "demand_authority_sha256": compatibility.demand_authority_sha256,
            "decision": compatibility.decision,
            "satisfied_dimensions": list(
                compatibility.satisfied_dimensions
            ),
            "constrained_dimensions": list(
                compatibility.constrained_dimensions
            ),
            "blocked_dimensions": list(compatibility.blocked_dimensions),
            "unknown_dimensions": list(compatibility.unknown_dimensions),
            "effective_constraints": list(
                compatibility.effective_constraints
            ),
            "disclosures": list(compatibility.disclosures),
            "reason_codes": list(compatibility.reason_codes),
            "schema_version": compatibility.schema_version,
        }

    def compute_authority_sha256(
        self,
        compatibility: OfferDemandCompatibility,
    ) -> str:
        return self.stable_sha256(
            self.authority_payload(compatibility)
        )

    def verify(self, compatibility: OfferDemandCompatibility) -> bool:
        return compatibility.authority_sha256 == (
            self.compute_authority_sha256(compatibility)
        )
