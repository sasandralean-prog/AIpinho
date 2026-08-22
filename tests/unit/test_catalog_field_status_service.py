from __future__ import annotations

from aipinho.services.artifacts.catalog_field_status_service import CatalogFieldStatusService


def test_catalog_field_status_preserves_inferred_as_not_truth() -> None:
    field = CatalogFieldStatusService().build(
        field_name="track_title",
        value="All I Want",
        status="inferred",
        source="filename",
        source_method="artist_title_separator_rule",
        confidence=0.72,
        limitations=["inferred_identity_not_observed_truth"],
        promoted_to_truth=False,
        safe_for_truth_claim=False,
    )

    assert field["status"] == "inferred"
    assert field["value"] == "All I Want"
    assert field["confidence"] == 0.72
    assert field["promoted_to_truth"] is False
    assert field["safe_for_truth_claim"] is False


def test_unknown_status_is_explicit_not_false() -> None:
    field = CatalogFieldStatusService().build(
        field_name="artist",
        value=None,
        status="unknown",
        source="row_applicability_policy",
        source_method="none",
    )

    assert field["status"] == "unknown"
    assert field["value"] is None
