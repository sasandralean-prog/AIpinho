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


def test_row_level_validation_separates_stable_identity_from_locator_display_and_truth() -> None:
    content = "entity_id,relative_path,filename,extension,evidence_ref\nentity_1,album/track.mp3,track.mp3,mp3,file:one\n"

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "relative_path", "filename", "extension", "evidence_ref"],
        required_columns=["entity_id", "relative_path", "filename", "extension", "evidence_ref"],
    )

    identity = summary.row_identity_coverage
    assert identity.rows_with_stable_entity_identity == 1
    assert identity.rows_with_locator_context == 1
    assert identity.rows_with_semantic_identity_evidence == 0
    assert identity.reason_code == "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert identity.truth_eligible_rows == 0
    assert identity.metadata["filename_path_extension_truth_authority"] is False
    assert "relative_path" in identity.locator_context_fields
    assert "extension" in identity.routing_hint_fields


def test_row_level_validation_full_semantic_identity_requires_evidence_ref() -> None:
    content = "entity_id,track_title,artist,evidence_ref\nentity_1,Track,Artist,file:one\n"

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "track_title", "artist", "evidence_ref"],
        required_columns=["entity_id", "track_title", "artist", "evidence_ref"],
    )

    identity = summary.row_identity_coverage
    assert identity.status == "satisfied"
    assert identity.reason_code is None
    assert identity.rows_with_semantic_identity_evidence == 1
    assert identity.observed_semantic_identity_fields == ["artist", "track_title"]
    assert identity.truth_eligible_rows == 0


def test_row_level_validation_semantic_identity_without_evidence_is_not_identity_truth() -> None:
    content = "entity_id,track_title,artist,evidence_ref\nentity_1,Track,Artist,\n"

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "track_title", "artist", "evidence_ref"],
        required_columns=["entity_id", "track_title", "artist", "evidence_ref"],
    )

    assert summary.row_identity_coverage.rows_with_semantic_identity_evidence == 0
    assert summary.row_identity_coverage.reason_code == "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert summary.row_evidence_coverage.reason_code == "ARTIFACT_EVIDENCE_BINDING_MISSING"


def test_row_level_validation_missing_identity_evidence_does_not_become_false() -> None:
    content = "entity_id,track_title,artist,evidence_ref\nentity_1,not_observed,,file:one\n"

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "track_title", "artist", "evidence_ref"],
        required_columns=["entity_id", "track_title", "artist", "evidence_ref"],
    )

    assert summary.row_identity_coverage.rows_with_semantic_identity_evidence == 0
    assert summary.row_identity_coverage.rows_without_semantic_identity_evidence == 1
    assert summary.truth_eligible is False
    assert summary.value_counts_by_column["entity_id"] == 1
    assert summary.absence_counts_by_column["track_title"]["not_observed"] == 1


def test_row_level_validation_caps_evidence_rows_to_rendered_rows() -> None:
    content = "entity_id,evidence_ref\nentity_1,file:one\n"

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "evidence_ref"],
        required_columns=["entity_id", "evidence_ref"],
        row_bindings=[
            {"entity_id": "entity_1", "evidence_refs": ["file:one"]},
            {"entity_id": "entity_2", "evidence_refs": ["file:two"]},
        ],
    )

    assert summary.row_evidence_coverage.total_rows == 1
    assert summary.row_evidence_coverage.rows_with_evidence_ref == 1
    assert summary.row_evidence_coverage.rows_without_evidence_ref == 0
