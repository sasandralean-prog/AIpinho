from __future__ import annotations

from aipinho.services.artifacts.media_inventory_sufficiency_service import MediaInventorySufficiencyService


def _row_validation(rows: int, semantic_identity_rows: int) -> dict:
    return {
        "status": "insufficient_evidence" if semantic_identity_rows < rows else "satisfied",
        "row_count": rows,
        "rows_with_required_identity": rows,
        "row_identity_coverage": {
            "total_rows": rows,
            "rows_with_stable_entity_identity": rows,
            "rows_with_semantic_identity_evidence": semantic_identity_rows,
            "rows_without_semantic_identity_evidence": max(0, rows - semantic_identity_rows),
            "stable_entity_identity_ratio": 1.0,
            "semantic_identity_evidence_ratio": semantic_identity_rows / max(1, rows),
            "status": "insufficient_evidence" if semantic_identity_rows < rows else "satisfied",
            "reason_code": "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT" if semantic_identity_rows < rows else None,
        },
        "row_evidence_coverage": {
            "total_rows": rows,
            "rows_with_evidence_ref": rows,
            "evidence_ref_count": rows,
            "status": "satisfied",
        },
    }


def test_sufficiency_uses_primary_media_identity_denominator_when_row_taxonomy_is_present() -> None:
    result = MediaInventorySufficiencyService().evaluate(
        expected_rows=4,
        selected_rows=4,
        bound_rows=4,
        evidence_ref_count=4,
        row_validation=_row_validation(rows=4, semantic_identity_rows=1),
        media_metadata_capability={"status": "partial", "attributes_missing": []},
        metadata_coverage={
            "files_attempted": 4,
            "files_succeeded": 2,
            "coverage_ratio": 0.5,
            "primary_media_files_attempted": 2,
            "primary_media_files_succeeded": 2,
            "primary_media_observation_ratio": 1.0,
        },
        schema_status="satisfied",
        row_applicability={
            "all_rows_count": 4,
            "primary_media_row_count": 2,
            "lyrics_sidecar_row_count": 1,
            "artwork_row_count": 1,
            "primary_media_with_governed_identity_count": 1,
            "primary_media_without_identity_tags_count": 1,
            "primary_media_backend_no_valid_evidence_count": 0,
            "primary_media_identity_ratio": 0.5,
            "candidate_identity_available_count": 2,
            "candidate_identity_not_truth_count": 2,
            "sidecar_relationship_candidate_count": 1,
            "artwork_candidate_count": 1,
            "technical_metadata_observed_count": 2,
            "technical_metadata_only_count": 1,
            "row_class_counts": {
                "primary_media_with_governed_identity": 1,
                "primary_media_without_identity_tags": 1,
                "lyrics_sidecar_candidate": 1,
                "artwork_candidate": 1,
            },
        },
    )

    assert result.status == "blocked"
    assert result.reason_code == "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT" not in result.reason_codes
    assert "MEDIA_PRIMARY_IDENTITY_TAGS_ABSENT" in result.reason_codes
    assert "MEDIA_CANDIDATE_IDENTITY_NOT_TRUTH" in result.reason_codes
    assert "MEDIA_SIDECAR_RELATIONSHIP_POLICY_REQUIRED" in result.reason_codes
    assert result.coverage_summary["primary_media_row_count"] == 2
    assert result.coverage_summary["primary_media_identity_ratio"] == 0.5
    assert result.coverage_summary["semantic_identity_evidence_ratio"] == 0.25
    assert result.safe_to_use is False


def test_container_mismatch_and_backend_no_valid_evidence_are_precise_blockers() -> None:
    result = MediaInventorySufficiencyService().evaluate(
        expected_rows=1,
        selected_rows=1,
        bound_rows=1,
        evidence_ref_count=1,
        row_validation=_row_validation(rows=1, semantic_identity_rows=0),
        media_metadata_capability={"status": "partial", "attributes_missing": []},
        metadata_coverage={
            "files_attempted": 1,
            "files_succeeded": 0,
            "coverage_ratio": 0.0,
            "primary_media_files_attempted": 1,
            "primary_media_files_succeeded": 0,
            "primary_media_observation_ratio": 0.0,
        },
        schema_status="satisfied",
        row_applicability={
            "all_rows_count": 1,
            "primary_media_row_count": 1,
            "primary_media_with_governed_identity_count": 0,
            "primary_media_without_identity_tags_count": 0,
            "primary_media_backend_no_valid_evidence_count": 1,
            "file_anatomy_extension_container_mismatch_count": 1,
            "candidate_identity_available_count": 1,
            "candidate_identity_not_truth_count": 1,
        },
    )

    assert result.reason_code == "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert "MEDIA_BACKEND_NO_VALID_EVIDENCE" in result.reason_codes
    assert "MEDIA_CONTAINER_EXTENSION_MISMATCH" in result.reason_codes
