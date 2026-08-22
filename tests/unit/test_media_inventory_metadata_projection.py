from __future__ import annotations

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService


def test_metadata_coverage_prefers_physical_backend_telemetry_over_legacy_attempt_maps() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()
    selected_entities = [{"entity_id": "entity_1"}, {"entity_id": "entity_2"}]
    payload = {
        "attribute_observations": [
            {
                "entity_id": "entity_1",
                "capability_id": "media_metadata_reader",
                "observation_state": "observed",
                "canonical_key": "duration",
                "observed_value": 1000,
                "provenance": {"backend_id": "mutagen"},
            }
        ],
        "media_metadata_capability": {
            "status": "partial",
            "configured": True,
            "available": True,
            "attempted_backends": {"mutagen": 1},
            "successful_backends": {},
        },
        "post_compile_observation_execution": {
            "physical_probe_count": 2,
            "files_attempted": 2,
            "files_succeeded": 1,
            "files_failed": 1,
            "physical_backend_attempts": {"mutagen": 2},
            "physical_backend_successes": {"mutagen": 1},
            "attempted_backends": {"mutagen": 1},
            "successful_backends": {},
        },
        "contract_observation_plan": {"attribute_contracts": []},
    }

    summary = service._metadata_coverage_summary(
        perception_payload=payload,
        selected_entities=selected_entities,
        row_applicability_summary={"primary_media_row_count": 2},
    )

    assert summary["attempted_backends"] == {"mutagen": 2}
    assert summary["successful_backends"] == {"mutagen": 1}
    assert summary["evidence_counts_by_backend"] == {"mutagen": 1}
    assert summary["telemetry_projection_source"]["execution_telemetry_present"] is True
