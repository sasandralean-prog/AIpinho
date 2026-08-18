from __future__ import annotations

import csv
import io

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ArtifactRenderResult,
    ReadonlyAnalysisArtifactRuntimeService,
)


MEDIA_INVENTORY_FIELDS = [
    "entity_id",
    "source_root_role",
    "relative_path",
    "filename",
    "extension",
    "media_type",
    "track_title",
    "artist",
    "album",
    "duration",
    "codec",
    "container",
    "bitrate",
    "sample_rate",
    "metadata_status",
    "evidence_ref",
    "limitations",
    "relationship_candidate_refs",
    "validation_status",
]


def _csv(row: dict[str, str]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=MEDIA_INVENTORY_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerow({field: row.get(field, "") for field in MEDIA_INVENTORY_FIELDS})
    return stream.getvalue()


def _render_result(content: str) -> ArtifactRenderResult:
    return ArtifactRenderResult(
        content=content,
        semantic_gaps=[],
        schema_coverage={},
        entity_summary={},
        partial_rows=1,
        expected_rows=1,
        rendered_columns=list(MEDIA_INVENTORY_FIELDS),
        missing_columns=[],
    )


def _contract() -> dict[str, object]:
    return {
        "contract_id": "media_corpus_inventory_artifact",
        "expected_kind": "media_corpus_inventory",
        "expected_schema": list(MEDIA_INVENTORY_FIELDS),
    }


def test_music_inventory_partial_preserves_semantic_shape_and_blocks_truth() -> None:
    content = _csv(
        {
            "entity_id": "entity_1",
            "source_root_role": "library_root",
            "relative_path": "collection/item.media",
            "filename": "item.media",
            "extension": "media",
            "media_type": "audio",
            "track_title": "unknown",
            "artist": "unknown",
            "album": "unknown",
            "duration": "not_configured",
            "codec": "not_configured",
            "container": "not_configured",
            "bitrate": "not_configured",
            "sample_rate": "not_configured",
            "metadata_status": "not_configured",
            "evidence_ref": "observed_entity:entity_1",
            "limitations": "metadata_capability_not_configured",
            "relationship_candidate_refs": "",
            "validation_status": "semantic_validation_required",
        }
    )

    decision = ReadonlyAnalysisArtifactRuntimeService()._semantic_artifact_render_decision(
        logical_path="reports/media/inventory.csv",
        content_type="text/csv",
        content=content,
        declared_contract=_contract(),
        render_result=_render_result(content),
    )

    assert decision["artifact_status"] == "partial"
    assert decision["validation_status"] == "partial"
    assert decision["semantic_contract_status"] == "partial"
    assert decision["reason_code"] == "MUSIC_INVENTORY_PARTIAL_EVIDENCE"
    assert decision["safe_to_use"] is False


def test_findings_shape_blocks_music_inventory_semantic_decision() -> None:
    content = "severity,title,summary\ninfo,Finding,Diagnostic only\n"

    decision = ReadonlyAnalysisArtifactRuntimeService()._semantic_artifact_render_decision(
        logical_path="reports/media/inventory.csv",
        content_type="text/csv",
        content=content,
        declared_contract=_contract(),
        render_result=_render_result(content),
    )

    assert decision["artifact_status"] == "blocked"
    assert decision["semantic_contract_status"] == "insufficient"
    assert decision["reason_code"] == "MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT"
    assert decision["safe_to_use"] is False


def test_budget_limited_render_cannot_be_promoted_to_ready_even_with_valid_shape() -> None:
    content = _csv(
        {
            "entity_id": "entity_1",
            "source_root_role": "library_root",
            "relative_path": "collection/item.media",
            "filename": "item.media",
            "extension": "media",
            "media_type": "audio",
            "track_title": "Track",
            "artist": "Artist",
            "album": "Album",
            "duration": "180",
            "codec": "observed",
            "container": "observed",
            "bitrate": "320000",
            "sample_rate": "44100",
            "metadata_status": "available",
            "evidence_ref": "observed_entity:entity_1",
            "limitations": "artifact_render_entity_budget_partial",
            "relationship_candidate_refs": "",
            "validation_status": "semantic_validation_required",
        }
    )
    render = _render_result(content)
    render = render.__class__(
        **{
            **render.__dict__,
            "status": "partial",
            "reason_code": "ARTIFACT_RENDER_PARTIAL",
            "partial_rows": 1,
            "expected_rows": 3,
            "safe_to_use": False,
        }
    )

    decision = ReadonlyAnalysisArtifactRuntimeService()._semantic_artifact_render_decision(
        logical_path="reports/media/inventory.csv",
        content_type="text/csv",
        content=content,
        declared_contract=_contract(),
        render_result=render,
    )

    assert decision["artifact_status"] == "blocked"
    assert decision["semantic_contract_status"] == "partial"
    assert decision["reason_code"] == "ARTIFACT_RENDER_PARTIAL"
    assert decision["safe_to_use"] is False
