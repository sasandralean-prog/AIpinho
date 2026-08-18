from aipinho.services.artifacts.row_level_semantic_validation_service import RowLevelSemanticValidationService


def test_row_level_validation_separates_rendered_columns_from_missing_values() -> None:
    content = (
        "entity_id,source_root_role,evidence_ref,codec,validation_status\n"
        "entity_1,library_root,file:one,not_observed,semantic_validation_required\n"
    )

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "source_root_role", "evidence_ref", "codec", "validation_status"],
        required_columns=["entity_id", "source_root_role", "evidence_ref", "codec", "validation_status"],
    )

    assert summary.column_coverage.missing_columns == []
    assert summary.row_evidence_coverage.evidence_ref_count == 1
    assert summary.row_evidence_coverage.evidence_refs_sample == ["file:one"]
    assert summary.missing_required_row_values["codec"] == 1
    assert summary.truth_eligible is False


def test_row_level_validation_reports_missing_evidence_ref_without_inventing_truth() -> None:
    content = "entity_id,source_root_role,evidence_ref\nentity_1,library_root,\n"

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "source_root_role", "evidence_ref"],
        required_columns=["entity_id", "source_root_role", "evidence_ref"],
    )

    assert summary.status == "partial"
    assert summary.row_evidence_coverage.status == "missing"
    assert summary.row_evidence_coverage.reason_code == "ARTIFACT_EVIDENCE_BINDING_MISSING"
    assert "ARTIFACT_ROW_EVIDENCE_PARTIAL" in summary.reason_codes


def test_row_level_validation_accepts_filename_as_name_alias() -> None:
    content = "entity_id,filename,evidence_ref\nentity_1,track.wav,file:one\n"

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "name", "evidence_ref"],
        required_columns=["entity_id", "name", "evidence_ref"],
    )

    assert summary.column_coverage.missing_columns == []
    assert summary.column_coverage.extra_columns == []
    assert summary.row_evidence_coverage.status == "satisfied"
