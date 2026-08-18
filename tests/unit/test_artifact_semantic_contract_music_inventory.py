from __future__ import annotations

import csv
import io

from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService


def _csv(rows: list[dict[str, str]], fieldnames: list[str]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _rich_inventory_content(*, metadata_status: str = "available") -> str:
    fields = [
        "entity_id",
        "source_root_role",
        "relative_path",
        "filename",
        "extension",
        "media_type",
        "size_bytes",
        "track_title",
        "artist",
        "album",
        "album_artist",
        "duration_ms",
        "codec",
        "container",
        "bitrate_bps",
        "sample_rate_hz",
        "channels",
        "artwork_present",
        "metadata_status",
        "metadata_source",
        "probe_status",
        "evidence_ref",
        "limitations",
        "relationship_candidate_refs",
        "validation_status",
    ]
    return _csv(
        [
            {
                "entity_id": "entity_1",
                "source_root_role": "library_root",
                "relative_path": "album/track.media",
                "filename": "track.media",
                "extension": "media",
                "media_type": "audio",
                "size_bytes": "1234",
                "track_title": "Track",
                "artist": "Artist",
                "album": "Album",
                "album_artist": "Artist",
                "duration_ms": "180000",
                "codec": "codec_observed",
                "container": "container_observed",
                "bitrate_bps": "320000",
                "sample_rate_hz": "44100",
                "channels": "2",
                "artwork_present": "unknown",
                "metadata_status": metadata_status,
                "metadata_source": "test_probe",
                "probe_status": "executed",
                "evidence_ref": "file:album/track.media",
                "limitations": "none_observed" if metadata_status == "available" else "metadata_not_configured",
                "relationship_candidate_refs": "",
                "validation_status": "semantic_validation_required",
            }
        ],
        fields,
    )


def test_findings_csv_does_not_satisfy_media_inventory_contract() -> None:
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/media/music_inventory.csv",
        content_type="text/csv",
        content='severity,title,summary\n"info","x","y"\n',
    )

    assert result.status == "blocked"
    assert result.contract_id == "media_corpus_inventory_artifact"
    assert "media_inventory_findings_shape_mismatch" in result.missing_requirements
    assert "artifact_schema_field_missing:entity id" in result.missing_requirements


def test_findings_csv_remains_valid_under_findings_contract_not_inventory() -> None:
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/analysis_findings.csv",
        content_type="text/csv",
        content='severity,title,summary\n"info","x","y"\n',
    )

    assert result.status == "passed"
    assert result.contract_id is None


def test_rich_media_inventory_satisfies_minimum_contract() -> None:
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/media/music_inventory.csv",
        content_type="text/csv",
        content=_rich_inventory_content(),
    )

    assert result.status == "passed"
    assert result.contract_id == "media_corpus_inventory_artifact"
    assert result.profile is not None
    assert result.profile.semantic_status == "passed"


def test_media_inventory_without_evidence_ref_blocks_semantic_success() -> None:
    service = ArtifactSemanticContractService()
    content = _rich_inventory_content().replace("file:album/track.media", "")

    result = service.validate(
        logical_path="reports/media/music_inventory.csv",
        content_type="text/csv",
        content=content,
    )

    assert result.status == "blocked"
    assert "media_inventory_evidence_ref_missing" in result.missing_requirements


def test_media_inventory_with_unavailable_metadata_is_partial_not_silent_success() -> None:
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/media/music_inventory.csv",
        content_type="text/csv",
        content=_rich_inventory_content(metadata_status="not_configured"),
    )

    assert result.status == "blocked"
    assert "media_inventory_metadata_capability_unavailable" in result.missing_requirements
    assert result.profile is not None
    assert any(
        gap.reason_code == "MUSIC_INVENTORY_PARTIAL_EVIDENCE"
        for gap in result.profile.semantic_gaps
    )
