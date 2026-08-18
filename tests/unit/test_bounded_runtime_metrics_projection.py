from __future__ import annotations

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)


def test_checkpoint_metadata_preserves_nested_payload_metrics_without_heavy_payload() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()

    bounded = service._bounded_checkpoint_metadata(  # noqa: SLF001 - projection contract
        {
            "payload_metrics": {
                "input_entity_count": 10,
                "projected_entity_count": 9,
                "attribute_observation_count": 18,
                "evidence_ref_count": 9,
                "projected_fact_count": 11,
                "payload_item_count": 200,
                "estimated_payload_bytes": 12345,
                "materialized_payload_bytes": 12000,
                "payload_ref_count": 1,
                "full_entities": [{"entity_id": "e1"}],
            },
            "raw_payload": "x" * 10000,
        }
    )

    assert bounded["payload_metrics"]["input_entity_count"] == 10
    assert bounded["payload_metrics"]["attribute_observation_count"] == 18
    assert bounded["payload_metrics"]["payload_ref_count"] == 1
    assert "full_entities" not in bounded["payload_metrics"]
    assert "raw_payload" not in bounded


def test_artifact_persist_checkpoint_metrics_are_bounded_and_generic() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()
    result = service._bounded_checkpoint_metadata(  # noqa: SLF001 - projection contract
        {
            "artifact_id": "artifact_generic",
            "payload_bytes": 1000,
            "serialized_bytes": 1000,
            "artifact_content_bytes": 900,
            "payload_ref_count": 1,
            "manifest_bytes": 300,
            "payload_ref_decision": "PAYLOAD_REF",
            "rows": ["not", "allowed"],
        }
    )

    assert result["payload_bytes"] == 1000
    assert result["payload_ref_decision"] == "PAYLOAD_REF"
    assert "rows" not in result
