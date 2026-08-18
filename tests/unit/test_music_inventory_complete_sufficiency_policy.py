from __future__ import annotations

from aipinho.services.artifacts.media_inventory_sufficiency_service import MediaInventorySufficiencyService


def _row_validation(*, rows: int, evidence_rows: int | None = None, identity_rows: int | None = None) -> dict:
    evidence_rows = rows if evidence_rows is None else evidence_rows
    identity_rows = rows if identity_rows is None else identity_rows
    return {
        "status": "satisfied",
        "row_count": rows,
        "rows_with_required_identity": identity_rows,
        "row_identity_coverage": {
            "total_rows": rows,
            "rows_with_stable_entity_identity": identity_rows,
            "rows_with_semantic_identity_evidence": identity_rows,
            "rows_without_semantic_identity_evidence": max(0, rows - identity_rows),
            "stable_entity_identity_ratio": 1.0 if rows and identity_rows == rows else 0.0,
            "semantic_identity_evidence_ratio": 1.0 if rows and identity_rows == rows else 0.0,
            "status": "satisfied" if rows and identity_rows == rows else "insufficient_evidence",
            "reason_code": None if rows and identity_rows == rows else "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT",
        },
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


def test_semantic_identity_evidence_insufficient_is_distinct_from_row_binding_identity() -> None:
    row_validation = _row_validation(rows=2, identity_rows=2)
    row_validation["row_identity_coverage"]["rows_with_semantic_identity_evidence"] = 1
    row_validation["row_identity_coverage"]["rows_without_semantic_identity_evidence"] = 1
    row_validation["row_identity_coverage"]["semantic_identity_evidence_ratio"] = 0.5
    row_validation["row_identity_coverage"]["status"] = "insufficient_evidence"
    row_validation["row_identity_coverage"]["reason_code"] = "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT"

    result = MediaInventorySufficiencyService().evaluate(
        expected_rows=2,
        selected_rows=2,
        bound_rows=2,
        evidence_ref_count=2,
        row_validation=row_validation,
        media_metadata_capability={"status": "partial", "attributes_missing": []},
        metadata_coverage={"files_attempted": 2, "files_succeeded": 2, "coverage_ratio": 1.0},
        schema_status="satisfied",
    )

    assert result.status == "blocked"
    assert result.reason_code == "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert "MEDIA_INVENTORY_IDENTITY_COVERAGE_INSUFFICIENT" not in result.reason_codes
    assert result.coverage_summary["stable_entity_identity_ratio"] == 1.0
    assert result.coverage_summary["semantic_identity_evidence_ratio"] == 0.5


def test_identity_coverage_uses_rendered_row_domain_not_selected_entity_domain() -> None:
    row_validation = _row_validation(rows=1, identity_rows=1)

    result = MediaInventorySufficiencyService().evaluate(
        expected_rows=2,
        selected_rows=2,
        bound_rows=2,
        evidence_ref_count=2,
        row_validation=row_validation,
        media_metadata_capability={"status": "partial", "attributes_missing": []},
        metadata_coverage={"files_attempted": 1, "files_succeeded": 1, "coverage_ratio": 1.0},
        schema_status="satisfied",
    )

    assert "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT" not in result.reason_codes
    assert result.coverage_summary["rows_rendered"] == 1
    assert result.coverage_summary["identity_coverage_ratio"] == 1.0
