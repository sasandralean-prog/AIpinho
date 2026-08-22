from __future__ import annotations

from aipinho.services.artifacts.media_inventory_row_taxonomy_service import MediaInventoryRowTaxonomyService
from aipinho.services.artifacts.media_inventory_sufficiency_service import MediaInventorySufficiencyService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService


def _attribute(value: object) -> dict:
    return {"value": value, "status": "observed", "evidence_ref": "file:test"}


def _entity(entity_id: str, *, name: str, extension: str, root: str, relative_path: str) -> dict:
    return {
        "entity_id": entity_id,
        "entity_kind": "file",
        "source_root": root,
        "source_root_role": "library_root",
        "relative_path": relative_path,
        "observed_attributes": {
            "name": _attribute(name),
            "extension": _attribute(extension),
            "relative_path": _attribute(relative_path),
            "source_root": _attribute(root),
            "source_root_role": _attribute("library_root"),
        },
        "evidence_refs": [f"file:{root}/{relative_path}"],
    }


def _row_validation(rows: int, semantic_identity_rows: int) -> dict:
    return {
        "status": "insufficient_evidence",
        "row_count": rows,
        "rows_with_required_identity": rows,
        "row_identity_coverage": {
            "total_rows": rows,
            "rows_with_stable_entity_identity": rows,
            "rows_with_semantic_identity_evidence": semantic_identity_rows,
            "rows_without_semantic_identity_evidence": rows - semantic_identity_rows,
            "stable_entity_identity_ratio": 1.0,
            "semantic_identity_evidence_ratio": semantic_identity_rows / max(1, rows),
            "status": "insufficient_evidence",
            "reason_code": "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT",
        },
        "row_evidence_coverage": {
            "total_rows": rows,
            "rows_with_evidence_ref": rows,
            "evidence_ref_count": rows,
            "status": "satisfied",
        },
    }


def test_b3_10_catalog_confidence_reframes_truth_blocker_for_planning(tmp_path) -> None:
    observed_path = tmp_path / "Tagged Song.m4a"
    observed_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    inferred_path = tmp_path / "A Day To Remember - All I Want.m4a"
    inferred_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    candidate_path = tmp_path / "505 - 2.m4a"
    candidate_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    lyrics_path = tmp_path / "A Day To Remember - All I Want.lrc"
    lyrics_path.write_text("[00:01.00]sample", encoding="utf-8")

    entities = [
        _entity("observed", name=observed_path.name, extension="m4a", root=str(tmp_path), relative_path=observed_path.name),
        _entity("inferred", name=inferred_path.name, extension="m4a", root=str(tmp_path), relative_path=inferred_path.name),
        _entity("candidate", name=candidate_path.name, extension="m4a", root=str(tmp_path), relative_path=candidate_path.name),
        _entity("lyrics", name=lyrics_path.name, extension="lrc", root=str(tmp_path), relative_path=lyrics_path.name),
    ]
    bindings = {
        "observed": {
            "track_title": [{"value": "Tagged Song", "evidence_refs": ["evidence:title"]}],
            "artist": [{"value": "Observed Artist", "evidence_refs": ["evidence:artist"]}],
        }
    }
    perception_payload = {
        "attribute_observations": [
            {
                "entity_id": "inferred",
                "capability_id": "media_metadata_reader",
                "observation_state": "observed",
                "canonical_key": "duration",
                "observed_value": 1000,
                "provenance": {"backend_id": "mutagen"},
            },
            {
                "entity_id": "candidate",
                "capability_id": "media_metadata_reader",
                "observation_state": "observed",
                "canonical_key": "duration",
                "observed_value": 1000,
                "provenance": {"backend_id": "mutagen"},
            },
        ]
    }

    taxonomy = MediaInventoryRowTaxonomyService().classify(
        selected_entities=entities,
        claim_evidence_bindings=bindings,
        perception_payload=perception_payload,
    )
    rows = taxonomy["rows_by_entity"]

    assert rows["observed"]["resolved_identity_source_status"] == "observed"
    assert rows["observed"]["safe_for_truth_claim"] is True
    assert rows["inferred"]["resolved_identity_source_status"] == "inferred"
    assert rows["inferred"]["safe_for_truth_claim"] is False
    assert rows["inferred"]["inferred_track_title"] == "All I Want"
    assert rows["candidate"]["resolved_identity_source_status"] == "candidate"
    assert rows["candidate"]["inferred_track_title"] is None
    assert rows["lyrics"]["track_title_status"] == "not_applicable"
    assert taxonomy["summary"]["rows_observed_identity"] == 1
    assert taxonomy["summary"]["rows_inferred_identity"] == 1
    assert taxonomy["summary"]["rows_candidate_identity"] == 1
    assert taxonomy["summary"]["rows_not_applicable_identity"] == 1
    assert taxonomy["summary"]["inventory_confidence"]["safe_for_truth_claim"] is False
    assert taxonomy["summary"]["inventory_confidence"]["safe_for_catalog"] is True
    assert taxonomy["summary"]["inventory_confidence"]["safe_for_planning"] == "true_with_limitations"

    sufficiency = MediaInventorySufficiencyService().evaluate(
        expected_rows=4,
        selected_rows=4,
        bound_rows=4,
        evidence_ref_count=4,
        row_validation=_row_validation(rows=4, semantic_identity_rows=1),
        media_metadata_capability={"status": "partial", "attributes_missing": []},
        metadata_coverage={
            "primary_media_files_attempted": 3,
            "primary_media_files_succeeded": 3,
            "primary_media_observation_ratio": 1.0,
        },
        schema_status="satisfied",
        row_applicability=taxonomy["summary"],
    )

    assert sufficiency.status == "blocked"
    assert sufficiency.safe_to_use is False
    assert sufficiency.use_safety["safe_for_truth_claim"] is False
    assert sufficiency.use_safety["safe_for_catalog"] is True
    assert sufficiency.use_safety["safe_for_planning"] == "true_with_limitations"
    assert sufficiency.use_safety["observed_identity_truth_claim_insufficient"] is True
    assert "CATALOG_INFERRED_IDENTITY_USED_WITH_LIMITATIONS" in sufficiency.reason_codes


def test_b3_10_artifact_summary_projects_use_safety_dimensions() -> None:
    artifact = {
        "artifact_id": "artifact_catalog",
        "logical_path": "reports/firetest5/music_inventory.csv",
        "status": "blocked",
        "validation_status": "blocked",
        "reason_code": "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT",
        "safe_to_use": False,
        "inventory_sufficiency_summary": {
            "use_safety": {
                "safe_for_truth_claim": False,
                "safe_for_catalog": True,
                "safe_for_planning": "true_with_limitations",
                "safe_for_downstream_static_analysis": "true_with_limitations",
                "safe_for_destructive_action": False,
                "safe_for_user_report": "true_with_limitations",
                "validation_status_for_truth_claim": "blocked",
                "validation_status_for_catalog": "passed",
                "validation_status_for_planning": "passed_with_limitations",
            },
            "coverage_summary": {
                "inventory_confidence": {
                    "safe_for_truth_claim": False,
                    "safe_for_catalog": True,
                    "safe_for_planning": "true_with_limitations",
                }
            },
        },
    }

    summary = ReadonlyAnalysisArtifactRuntimeService()._terminal_artifact_summary(artifact)  # noqa: SLF001 - projection regression

    assert summary["safe_to_use"] is False
    assert summary["safe_for_truth_claim"] is False
    assert summary["safe_for_catalog"] is True
    assert summary["safe_for_planning"] == "true_with_limitations"
    assert summary["validation_status_for_truth_claim"] == "blocked"
    assert summary["validation_status_for_catalog"] == "passed"
    assert summary["validation_status_for_planning"] == "passed_with_limitations"
