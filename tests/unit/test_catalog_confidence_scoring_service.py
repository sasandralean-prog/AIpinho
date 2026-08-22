from __future__ import annotations

from aipinho.services.artifacts.catalog_confidence_scoring_service import CatalogConfidenceScoringService


def test_technical_metadata_without_identity_scores_catalog_not_truth() -> None:
    scores = CatalogConfidenceScoringService().score_row(
        row_class="primary_media_without_identity_tags",
        technical_observed=True,
        identity_status="unknown",
        identity_confidence=0.0,
        container_confidence=0.95,
        extension_container_mismatch=False,
        relationship_candidate=False,
        has_entity_binding=True,
    )

    assert scores["technical_score"] > 0.8
    assert scores["identity_observed_score"] == 0.0
    assert scores["truth_claim_confidence"] == 0.0
    assert scores["planning_confidence"] > scores["truth_claim_confidence"]
    assert scores["catalog_item_status"] == "cataloged_partial"


def test_container_mismatch_lowers_container_and_truth_confidence() -> None:
    scores = CatalogConfidenceScoringService().score_row(
        row_class="primary_media_backend_no_valid_evidence",
        technical_observed=False,
        identity_status="container_mismatch",
        identity_confidence=0.0,
        container_confidence=0.9,
        extension_container_mismatch=True,
        relationship_candidate=False,
        has_entity_binding=True,
    )

    assert scores["container_score"] <= 0.35
    assert scores["truth_claim_confidence"] == 0.0
    assert scores["catalog_item_status"] == "cataloged_container_mismatch"
