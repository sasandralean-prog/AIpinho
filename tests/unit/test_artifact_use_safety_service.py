from __future__ import annotations

from aipinho.services.artifacts.artifact_use_safety_service import ArtifactUseSafetyService


def test_catalog_artifact_can_be_planning_safe_without_truth_claim_safety() -> None:
    safety = ArtifactUseSafetyService().evaluate_catalog_artifact(
        inventory_confidence={
            "safe_for_truth_claim": False,
            "safe_for_catalog": True,
            "safe_for_planning": "true_with_limitations",
        },
        reason_codes=[
            "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT",
            "CATALOG_OBSERVED_IDENTITY_INCOMPLETE",
        ],
        limitations=["primary_media_semantic_identity_evidence_incomplete"],
    )

    assert safety["safe_for_truth_claim"] is False
    assert safety["safe_for_catalog"] is True
    assert safety["safe_for_planning"] == "true_with_limitations"
    assert safety["safe_for_destructive_action"] is False
    assert safety["observed_identity_truth_claim_insufficient"] is True
    assert safety["planning_safe_with_limitations"] is True
