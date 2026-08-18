from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def _graph(count: int) -> dict:
    return {
        "entities": [
            {
                "entity_id": f"entity_{index}",
                "entity_kind": "generic",
                "confidence": 1.0,
                "source_root_role": "library_root",
                "entity_role": "record",
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


def test_fact_projection_bound_exceeded_blocks_explicitly() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph=_graph(3),
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name"],
            "perception_compile_policy": {
                "mode": "compile_only",
                "max_projected_facts": 1,
            },
        },
    )

    assert result.internal_reason_code == "PERCEPTION_FACT_PROJECTION_BOUND_EXCEEDED"
    assert result.semantic_self_review.can_speaker_claim is False
    assert "PERCEPTION_FACT_PROJECTION_BOUND_EXCEEDED" in result.semantic_coverage_2.blocking_reasons


def test_fact_budget_exceeded_does_not_silently_truncate() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph=_graph(2),
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name"],
            "perception_compile_policy": {
                "mode": "compile_only",
                "max_facts_per_entity": 0.1,
            },
        },
    )

    assert result.internal_reason_code == "PERCEPTION_FACT_PROJECTION_BOUND_EXCEEDED"
    assert result.payload_metrics["projected_fact_count"] >= 2
    assert result.semantic_self_review.can_speaker_claim is False
