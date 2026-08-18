from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def test_observation_binding_emits_internal_bounded_checkpoints() -> None:
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
                            "evidence_refs": ["name_ref_1"],
                        }
                    },
                }
            ]
        },
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name", "external_signal"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    stages = [item["stage"] for item in result.compile_stage_trace]
    assert "before_observation_goal_projection" in stages
    assert "after_observation_goal_projection" in stages
    assert "before_observation_strategy_projection" in stages
    assert "after_observation_strategy_projection" in stages
    assert "before_capability_match_projection" in stages
    assert "after_capability_match_projection" in stages
    assert "before_capability_decision_projection" in stages
    assert "after_capability_decision_projection" in stages
    assert "before_observation_task_projection" in stages
    assert "after_observation_task_projection" in stages
    assert "before_observation_requirement_projection" in stages
    assert "after_observation_requirement_projection" in stages
    assert all(item.get("bounded") is True for item in result.compile_stage_trace)
