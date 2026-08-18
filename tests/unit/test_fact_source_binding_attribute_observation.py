from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def test_source_binding_distinguishes_observed_missing_and_unsupported_observations() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph={
            "entities": [
                {
                    "entity_id": "entity_with_name",
                    "entity_kind": "generic",
                    "confidence": 1.0,
                    "source_root_role": "library_root",
                    "entity_role": "record",
                    "evidence_refs": ["entity_ref"],
                    "observed_attributes": {
                        "name": {
                            "value": "observed",
                            "status": "observed",
                            "confidence": 1.0,
                            "evidence_refs": ["name_ref"],
                        }
                    },
                }
            ]
        },
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name", "not_available_signal"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    states = {item.attribute_name: item.observation_state for item in result.attribute_observations}
    assert states["name"] == "observed"
    assert states["not_available_signal"] == "unsupported"
    assert result.payload_metrics["attribute_observation_count"] == 2
    assert result.payload_metrics["unsupported_observation_count"] == 1
    assert result.payload_metrics["missing_observation_count"] == 0
