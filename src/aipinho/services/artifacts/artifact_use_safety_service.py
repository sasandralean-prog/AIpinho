from __future__ import annotations

from typing import Any


class ArtifactUseSafetyService:
    """Evaluates artifact use safety across truth, catalog, and planning dimensions."""

    @classmethod
    def governed_dimensions(cls) -> tuple[str, ...]:
        """Dimensions emitted by this authority boundary.

        Semantic reasoners may select from these identifiers, but never create
        new dimensions on behalf of this service.
        """
        return tuple(cls.governed_dimension_states())

    @classmethod
    def governed_dimension_states(cls) -> dict[str, tuple[bool | str, ...]]:
        """Minimal typed vocabulary for use-safety emitted by this service."""
        return {
            "safe_for_truth_claim": (True, False),
            "safe_for_catalog": (True, False),
            "safe_for_planning": (True, "true_with_limitations", False),
            "safe_for_downstream_static_analysis": (
                True,
                "true_with_limitations",
                False,
            ),
            "safe_for_destructive_action": (True, False),
            "safe_for_user_report": (True, "true_with_limitations", False),
        }

    @classmethod
    def governed_requirement_states(cls) -> dict[str, tuple[bool | str, ...]]:
        """States that may satisfy a downstream safety requirement."""
        return {
            "safe_for_truth_claim": (True,),
            "safe_for_catalog": (True,),
            "safe_for_planning": (True, "true_with_limitations"),
            "safe_for_downstream_static_analysis": (
                True,
                "true_with_limitations",
            ),
            "safe_for_destructive_action": (True,),
            "safe_for_user_report": (True, "true_with_limitations"),
        }

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
