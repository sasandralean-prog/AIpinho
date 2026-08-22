from __future__ import annotations

from typing import Any


class ArtifactUseSafetyService:
    """Evaluates artifact use safety across truth, catalog, and planning dimensions."""

    def evaluate_catalog_artifact(
        self,
        *,
        inventory_confidence: dict[str, Any],
        reason_codes: list[str],
        limitations: list[str],
    ) -> dict[str, Any]:
        truth_safe = bool(inventory_confidence.get("safe_for_truth_claim"))
        catalog_safe = bool(inventory_confidence.get("safe_for_catalog"))
        planning_safe = inventory_confidence.get("safe_for_planning")
        if planning_safe is True:
            planning_state: bool | str = True
        elif planning_safe == "true_with_limitations" or catalog_safe:
            planning_state = "true_with_limitations"
        else:
            planning_state = False
        safe_for_report: bool | str = True if truth_safe else "true_with_limitations" if catalog_safe else False
        return {
            "safe_for_truth_claim": truth_safe,
            "safe_for_catalog": catalog_safe,
            "safe_for_planning": planning_state,
            "safe_for_downstream_static_analysis": "true_with_limitations" if catalog_safe else False,
            "safe_for_destructive_action": False,
            "safe_for_user_report": safe_for_report,
            "observed_identity_truth_claim_insufficient": "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT" in reason_codes
            or "CATALOG_OBSERVED_IDENTITY_INCOMPLETE" in reason_codes,
            "catalog_complete_with_inferred_unknown_status": catalog_safe,
            "planning_safe_with_limitations": planning_state == "true_with_limitations",
            "reason_codes": list(dict.fromkeys(reason_codes)),
            "limitations": list(dict.fromkeys(limitations)),
        }
