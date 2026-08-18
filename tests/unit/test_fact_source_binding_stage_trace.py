from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def _generic_graph(count: int = 3) -> dict:
    return {
        "entities": [
            {
                "entity_id": f"entity_{index}",
                "entity_kind": "generic",
                "confidence": 1.0,
                "source_root_role": "library_root",
                "entity_role": "record",
                "evidence_refs": [f"entity_evidence_{index}"],
                "observed_attributes": {
                    "name": {
                        "value": f"record {index}",
                        "status": "observed",
                        "confidence": 0.95,
                        "evidence_refs": [f"name_evidence_{index}"],
                    }
                },
            }
            for index in range(count)
        ]
    }


def test_fact_source_binding_emits_bounded_internal_stage_trace() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph=_generic_graph(),
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name", "missing_signal"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    stages = [item["stage"] for item in result.compile_stage_trace]
    assert "before_fact_source_binding" in stages
    assert "before_source_index_build" in stages
    assert "after_source_index_build" in stages
    assert "before_attribute_observation_projection" in stages
    assert "attribute_observation_projection_checkpoint" in stages
    assert "after_attribute_observation_projection" in stages
    assert "before_evidence_ref_resolution" in stages
    assert "after_evidence_ref_resolution" in stages
    assert "before_evidence_set_materialization" in stages
    assert "after_evidence_set_materialization" in stages
    assert "before_source_provenance_binding" in stages
    assert "after_source_provenance_binding" in stages
    assert "before_source_binding_bound_check" in stages
    assert "after_source_binding_bound_check" in stages
    assert "fact_source_binding_completed" in stages
    assert "after_fact_source_binding" in stages
    assert all(item.get("bounded") is True for item in result.compile_stage_trace)
    assert all("entities" not in item and "rows" not in item and "facts" not in item for item in result.compile_stage_trace)
