from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def test_source_binding_materializes_evidence_refs_without_copying_full_payloads_to_trace() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph={
            "entities": [
                {
                    "entity_id": "entity_1",
                    "entity_kind": "generic",
                    "confidence": 1.0,
                    "source_root_role": "library_root",
                    "entity_role": "record",
                    "evidence_refs": ["entity_ref_1"],
                    "observed_attributes": {
                        "name": {
                            "value": "alpha",
                            "status": "observed",
                            "confidence": 1.0,
                            "evidence_refs": ["shared_ref", "shared_ref"],
                        }
                    },
                }
            ]
        },
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    assert result.payload_metrics["evidence_ref_count"] >= 1
    assert result.payload_metrics["unique_evidence_ref_count"] >= 1
    assert result.payload_metrics["evidence_set_count"] == 1
    assert result.payload_metrics["evidence_record_count"] >= 1
    assert all("evidence_set" not in item for item in result.compile_stage_trace)
