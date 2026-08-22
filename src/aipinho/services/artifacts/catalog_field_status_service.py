from __future__ import annotations

from typing import Any

from aipinho.services.artifacts.catalog_confidence_model import FIELD_EPISTEMIC_STATUSES, build_catalog_field


class CatalogFieldStatusService:
    """Builds generic field epistemic status records for catalog artifacts."""

    statuses = FIELD_EPISTEMIC_STATUSES

    def build(
        self,
        *,
        field_name: str,
        value: Any,
        status: str,
        source: str,
        source_method: str,
        evidence_refs: list[str] | None = None,
        confidence: float = 0.0,
        limitations: list[str] | None = None,
        risk_flags: list[str] | None = None,
        promoted_to_truth: bool = False,
        safe_for_truth_claim: bool = False,
    ) -> dict[str, Any]:
        return build_catalog_field(
            field_name=field_name,
            value=value,
            status=status,
            source=source,
            source_method=source_method,
            evidence_refs=evidence_refs or [],
            confidence=confidence,
            limitations=limitations or [],
            risk_flags=risk_flags or [],
            promoted_to_truth=promoted_to_truth,
            safe_for_truth_claim=safe_for_truth_claim,
        )
