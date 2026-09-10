from __future__ import annotations

from aipinho.services.artifacts.media_inventory_sufficiency_service import (
    MediaInventorySufficiencyService,
)


def _validation(*, rendered: int, evidenced: int) -> dict:
    return {
        "row_count": rendered,
        "rows_with_required_identity": rendered,
        "row_identity_coverage": {
            "rows_with_stable_entity_identity": rendered,
            "rows_with_semantic_identity_evidence": 0,
        },
        "row_evidence_coverage": {
            "rows_with_evidence_ref": evidenced,
        },
    }


def _evaluate(*, selected: int, bound: int, rendered: int, evidenced: int):
    return MediaInventorySufficiencyService().evaluate(
        expected_rows=selected,
        selected_rows=selected,
        bound_rows=bound,
        evidence_ref_count=bound,
        row_validation=_validation(rendered=rendered, evidenced=evidenced),
        media_metadata_capability={"status": "partial", "attributes_missing": []},
        metadata_coverage={
            "files_attempted": rendered,
            "files_succeeded": rendered,
            "coverage_ratio": 1.0,
        },
        schema_status="satisfied",
    )


def test_rendered_row_evidence_uses_rendered_row_domain() -> None:
    result = _evaluate(selected=1305, bound=1305, rendered=1263, evidenced=1263)

    assert "ARTIFACT_EVIDENCE_BINDING_MISSING" not in result.reason_codes
    assert result.coverage_summary["selection_binding_coverage_ratio"] == 1.0
    assert result.coverage_summary["rendered_row_evidence_coverage_ratio"] == 1.0
    assert result.coverage_summary["evidence_coverage_ratio"] == 1.0


def test_missing_rendered_row_evidence_remains_a_blocker() -> None:
    result = _evaluate(selected=4, bound=4, rendered=4, evidenced=3)

    assert result.status == "blocked"
    assert result.reason_code == "ARTIFACT_EVIDENCE_BINDING_MISSING"
    assert result.coverage_summary["rendered_row_evidence_coverage_ratio"] == 0.75


def test_missing_selection_binding_remains_distinct_from_rendered_evidence() -> None:
    result = _evaluate(selected=4, bound=3, rendered=3, evidenced=3)

    assert result.status == "blocked"
    assert result.reason_code == "ARTIFACT_EVIDENCE_BINDING_MISSING"
    assert result.coverage_summary["selection_binding_coverage_ratio"] == 0.75
    assert result.coverage_summary["rendered_row_evidence_coverage_ratio"] == 1.0
