from __future__ import annotations

from aipinho.services.artifacts.media_inventory_sufficiency_service import MediaInventorySufficiencyService


def _row_validation(*, rows: int, evidence_rows: int | None = None, identity_rows: int | None = None) -> dict:
    evidence_rows = rows if evidence_rows is None else evidence_rows
    identity_rows = rows if identity_rows is None else identity_rows
    return {
        "status": "satisfied",
        "rows_with_required_identity": identity_rows,
        "row_evidence_coverage": {
            "total_rows": rows,
            "rows_with_evidence_ref": evidence_rows,
            "status": "satisfied" if evidence_rows == rows else "partial",
        },
    }


def test_selected_rows_below_expected_blocks_without_sampling_contract() -> None:
    result = MediaInventorySufficiencyService().evaluate(
        expected_rows=1051,
        selected_rows=100,
        bound_rows=100,
        evidence_ref_count=100,
        row_validation=_row_validation(rows=100),
        media_metadata_capability={"status": "partial", "attributes_missing": []},
        metadata_coverage={"files_attempted": 100, "files_succeeded": 100, "coverage_ratio": 1.0},
        schema_status="satisfied",
    )

    assert result.status == "blocked"
    assert result.reason_code == "MEDIA_INVENTORY_COVERAGE_INSUFFICIENT"
    assert result.safe_to_use is False


def test_full_evidence_and_metadata_coverage_allows_phase1_discovery_but_not_full_truth_when_fields_missing() -> None:
    result = MediaInventorySufficiencyService().evaluate(
        expected_rows=2,
        selected_rows=2,
        bound_rows=2,
        evidence_ref_count=2,
        row_validation=_row_validation(rows=2),
        media_metadata_capability={"status": "partial", "attributes_missing": ["duration"]},
        metadata_coverage={"files_attempted": 2, "files_succeeded": 2, "coverage_ratio": 1.0},
        schema_status="satisfied",
    )

    assert result.status == "satisfied"
    assert result.safe_to_use is True
    assert result.use_safety["phase1_discovery"] is True
    assert result.use_safety["full_truth_claim"] is False


def test_missing_metadata_probe_blocks_complete_inventory_sufficiency() -> None:
    result = MediaInventorySufficiencyService().evaluate(
        expected_rows=2,
        selected_rows=2,
        bound_rows=2,
        evidence_ref_count=2,
        row_validation=_row_validation(rows=2),
        media_metadata_capability={"status": "not_configured"},
        metadata_coverage={"files_attempted": 0, "files_succeeded": 0, "coverage_ratio": 0.0},
        schema_status="satisfied",
    )

    assert result.status == "blocked"
    assert "MEDIA_METADATA_PROBE_NOT_RUN" in result.reason_codes
    assert "MEDIA_METADATA_CAPABILITY_NOT_CONFIGURED" in result.reason_codes
