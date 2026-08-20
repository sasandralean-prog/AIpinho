from __future__ import annotations

import hashlib
import json

from aipinho.services.artifacts.media_inventory_sufficiency_service import MediaInventorySufficiencyService
from aipinho.services.artifacts.row_level_semantic_validation_service import RowLevelSemanticValidationService


def _summary_digest(summary: dict) -> str:
    payload = json.dumps(summary, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _claim_binding(entity_id: str = "entity_1", *, key: str = "track_title", value: str = "Song", evidence_ref: str = "evidence:title") -> dict:
    return {
        "entity_id": entity_id,
        "evidence_refs": [evidence_ref],
        "identity_claim_evidence": {
            key: [
                {
                    "value": value,
                    "evidence_refs": [evidence_ref],
                    "provenance_refs": ["raw:one"],
                    "observer_id": "media_metadata_reader",
                    "capability_id": "media_metadata_reader",
                }
            ]
        },
    }


def _evaluate(content: str, *, metadata_coverage: dict | None = None, row_bindings: list[dict] | None = None) -> dict:
    row_validation = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=list(content.splitlines()[0].split(",")),
        required_columns=list(content.splitlines()[0].split(",")),
        row_bindings=row_bindings,
    ).model_dump(mode="json")
    result = MediaInventorySufficiencyService().evaluate(
        expected_rows=row_validation["row_count"],
        selected_rows=row_validation["row_count"],
        bound_rows=row_validation["row_count"],
        evidence_ref_count=row_validation["row_evidence_coverage"]["evidence_ref_count"],
        row_validation=row_validation,
        media_metadata_capability={"status": "partial", "attributes_missing": []},
        metadata_coverage=metadata_coverage or {"files_attempted": row_validation["row_count"], "files_succeeded": row_validation["row_count"], "coverage_ratio": 1.0},
        schema_status="satisfied",
    )
    return {"row_validation": row_validation, "sufficiency": result.model_dump(mode="json")}


def test_identity_with_full_evidence_is_still_not_speaker_truth() -> None:
    observed = _evaluate(
        "entity_id,track_title,artist,evidence_ref\nentity_1,Song,Artist,file:one\n",
        row_bindings=[
            _claim_binding(key="track_title", value="Song", evidence_ref="evidence:title"),
            _claim_binding(key="artist", value="Artist", evidence_ref="evidence:artist"),
        ],
    )

    identity = observed["row_validation"]["row_identity_coverage"]
    assert identity["status"] == "satisfied"
    assert observed["sufficiency"]["status"] == "satisfied"
    assert identity["truth_eligible_rows"] == 0


def test_identity_partial_missing_unsupported_and_failed_observations_do_not_become_truth() -> None:
    observed = _evaluate(
        "entity_id,track_title,artist,evidence_ref\n"
        "entity_1,Song,Artist,file:one\n"
        "entity_2,not_observed,unsupported,file:two\n"
        "entity_3,blocked,,file:three\n",
        row_bindings=[_claim_binding()],
    )

    identity = observed["row_validation"]["row_identity_coverage"]
    assert identity["rows_with_semantic_identity_evidence"] == 1
    assert identity["rows_without_semantic_identity_evidence"] == 2
    assert observed["sufficiency"]["reason_code"] == "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert observed["row_validation"]["truth_eligible"] is False


def test_candidate_identity_and_duplicate_candidates_are_not_truth() -> None:
    observed = RowLevelSemanticValidationService().summarize_csv(
        content=(
            "entity_id,relationship_candidate_refs,track_title,evidence_ref\n"
            "entity_1,candidate:a;candidate:a,Song,file:one\n"
        ),
        declared_columns=["entity_id", "relationship_candidate_refs", "track_title", "evidence_ref"],
        required_columns=["entity_id", "relationship_candidate_refs", "track_title", "evidence_ref"],
    ).model_dump(mode="json")

    assert observed["truth_eligible"] is False
    assert observed["row_identity_coverage"]["rows_with_semantic_identity_evidence"] == 0
    assert observed["absence_counts_by_column"].get("relationship_candidate_refs") is None


def test_filename_path_and_extension_are_not_identity_authority() -> None:
    observed = _evaluate("entity_id,relative_path,filename,extension,evidence_ref\nentity_1,a/Song.mp3,Song.mp3,mp3,file:one\n")

    identity = observed["row_validation"]["row_identity_coverage"]
    assert identity["rows_with_stable_entity_identity"] == 1
    assert identity["rows_with_semantic_identity_evidence"] == 0
    assert identity["reason_code"] == "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert identity["metadata"]["filename_path_extension_truth_authority"] is False


def test_evidence_and_provenance_binding_are_reported_without_truth_promotion() -> None:
    observed = _evaluate("entity_id,track_title,artist,evidence_ref\nentity_1,Song,Artist,file:one;provenance:one\n")

    row_evidence = observed["row_validation"]["row_evidence_coverage"]
    assert row_evidence["rows_with_evidence_ref"] == 1
    assert row_evidence["evidence_ref_count"] == 2
    assert observed["row_validation"]["row_identity_coverage"]["rows_with_semantic_identity_evidence"] == 0
    assert observed["row_validation"]["row_identity_coverage"]["truth_eligible_rows"] == 0


def test_identity_digest_is_deterministic_for_same_evidence() -> None:
    first = _evaluate("entity_id,track_title,artist,evidence_ref\nentity_1,Song,Artist,file:one\n", row_bindings=[_claim_binding()])
    second = _evaluate("entity_id,track_title,artist,evidence_ref\nentity_1,Song,Artist,file:one\n", row_bindings=[_claim_binding()])

    assert _summary_digest(first["row_validation"]["row_identity_coverage"]) == _summary_digest(second["row_validation"]["row_identity_coverage"])


def test_metadata_completeness_is_distinct_from_identity_completeness() -> None:
    observed = _evaluate(
        "entity_id,track_title,artist,evidence_ref\nentity_1,Song,Artist,file:one\n",
        row_bindings=[_claim_binding()],
        metadata_coverage={"files_attempted": 1, "files_succeeded": 0, "coverage_ratio": 0.0},
    )

    assert "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT" not in observed["sufficiency"]["reason_codes"]
    assert "MEDIA_METADATA_OBSERVATION_INCOMPLETE" in observed["sufficiency"]["reason_codes"]


def test_generic_metadata_evidence_does_not_satisfy_identity_claim() -> None:
    observed = _evaluate(
        "entity_id,track_title,artist,evidence_ref\nentity_1,Song,Artist,evidence:metadata\n",
        row_bindings=[
            {
                "entity_id": "entity_1",
                "evidence_refs": ["evidence:metadata"],
                "identity_claim_evidence": {
                    "metadata": [
                        {
                            "value": {"artist": "Artist"},
                            "evidence_refs": ["evidence:metadata"],
                            "capability_id": "media_metadata_reader",
                        }
                    ]
                },
            }
        ],
    )

    identity = observed["row_validation"]["row_identity_coverage"]
    assert identity["rows_with_semantic_identity_evidence"] == 0
    assert observed["sufficiency"]["reason_code"] == "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT"


def test_identity_claim_evidence_must_match_entity_key_and_value() -> None:
    wrong_entity = _evaluate(
        "entity_id,track_title,evidence_ref\nentity_1,Song,file:one\n",
        row_bindings=[_claim_binding(entity_id="entity_2", key="track_title", value="Song")],
    )
    wrong_key = _evaluate(
        "entity_id,track_title,evidence_ref\nentity_1,Song,file:one\n",
        row_bindings=[_claim_binding(key="artist", value="Song")],
    )
    wrong_value = _evaluate(
        "entity_id,track_title,evidence_ref\nentity_1,Song,file:one\n",
        row_bindings=[_claim_binding(key="track_title", value="Other")],
    )

    assert wrong_entity["row_validation"]["row_identity_coverage"]["rows_with_semantic_identity_evidence"] == 0
    assert wrong_key["row_validation"]["row_identity_coverage"]["rows_with_semantic_identity_evidence"] == 0
    assert wrong_value["row_validation"]["row_identity_coverage"]["rows_with_semantic_identity_evidence"] == 0
