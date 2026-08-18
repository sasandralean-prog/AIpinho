from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def _large_graph(count: int) -> dict:
    return {
        "entities": [
            {
                "entity_id": f"entity_{index}",
                "entity_kind": "generic",
                "confidence": 1.0,
                "source_root_role": "library_root",
                "entity_role": "record",
                "evidence_refs": [f"entity_ref_{index}"],
                "observed_attributes": {
                    "name": {
                        "value": f"record {index}",
                        "status": "observed",
                        "confidence": 1.0,
                        "evidence_refs": [f"name_ref_{index}"],
                    }
                },
            }
            for index in range(count)
        ]
    }


def test_source_binding_bound_exceeded_blocks_without_silent_truncation() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph=_large_graph(4),
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name"],
            "perception_compile_policy": {
                "mode": "compile_only",
                "max_attribute_observations": 2,
            },
        },
    )

    assert result.internal_reason_code == "PERCEPTION_FACT_SOURCE_BINDING_BOUND_EXCEEDED"
    assert result.payload_metrics["reason_code"] == "PERCEPTION_FACT_SOURCE_BINDING_BOUND_EXCEEDED"
    assert result.payload_metrics["attribute_observation_count"] == 4
    assert result.semantic_self_review.can_speaker_claim is False
