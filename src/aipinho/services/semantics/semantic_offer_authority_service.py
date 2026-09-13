from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.semantics.semantic_offer import SemanticOffer


class SemanticOfferAuthorityService:
    """Computes and verifies immutable producer-local semantic offers."""

    def stable_sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def authority_payload(self, offer: SemanticOffer) -> dict[str, Any]:
        return {
            "semantic_graph_id": offer.semantic_graph_id,
            "semantic_graph_authority_sha256": (
                offer.semantic_graph_authority_sha256
            ),
            "producer_work_unit_id": offer.producer_work_unit_id,
            "vocabulary_binding": offer.vocabulary_binding.model_dump(mode="json"),
            "status": offer.status,
            "result_status": offer.result_status,
            "result_ref": offer.result_ref,
            "source_step_ids": list(offer.source_step_ids),
            "use_safety": dict(offer.use_safety),
            "semantic_properties": dict(offer.semantic_properties),
            "allowed_downstream_uses": list(offer.allowed_downstream_uses),
            "evidence_domains": list(offer.evidence_domains),
            "observed_effects": list(offer.observed_effects),
            "evidence_refs": list(offer.evidence_refs),
            "artifact_refs": list(offer.artifact_refs),
            "limitations": list(offer.limitations),
            "missing_truth": list(offer.missing_truth),
            "required_disclosures": list(offer.required_disclosures),
            "risk_constraints": list(offer.risk_constraints),
            "source_provenance": dict(offer.source_provenance),
            "reason_codes": list(offer.reason_codes),
            "schema_version": offer.schema_version,
        }

    def compute_authority_sha256(self, offer: SemanticOffer) -> str:
        return self.stable_sha256(self.authority_payload(offer))

    def verify(self, offer: SemanticOffer) -> bool:
        return offer.authority_sha256 == self.compute_authority_sha256(offer)
