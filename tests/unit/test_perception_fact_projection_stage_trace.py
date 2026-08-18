from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def _generic_graph(count: int = 2) -> dict:
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


def test_fact_projection_has_bounded_internal_stage_trace() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph=_generic_graph(),
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    stages = [item["stage"] for item in result.compile_stage_trace]
    assert "before_fact_projection" in stages
    assert "before_fact_source_binding" in stages
    assert "after_fact_source_binding" in stages
    assert "before_fact_candidate_projection" in stages
    assert "after_fact_candidate_projection" in stages
    assert "before_fact_derivation" in stages
    assert "fact_derivation_checkpoint" in stages
    assert "after_fact_derivation" in stages
    assert "before_fact_provenance_binding" in stages
    assert "after_fact_provenance_binding" in stages
    assert "before_fact_deduplication" in stages
    assert "after_fact_deduplication" in stages
    assert "before_fact_validation_projection" in stages
    assert "after_fact_validation_projection" in stages
    assert "fact_projection_completed" in stages
    assert "after_fact_projection" in stages
    assert all(item.get("bounded") is True for item in result.compile_stage_trace)
    assert all("entities" not in item and "facts" not in item for item in result.compile_stage_trace)


def test_fact_projection_metrics_are_bounded_counts() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph=_generic_graph(count=3),
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    metrics = result.payload_metrics
    assert metrics["projected_fact_count"] >= 3
    assert metrics["observed_fact_count"] >= 3
    assert metrics["candidate_fact_count"] == 0
    assert metrics["facts_with_evidence_count"] >= 3
    assert metrics["facts_with_provenance_count"] >= 3
    assert metrics["truth_eligible_count"] >= 1
