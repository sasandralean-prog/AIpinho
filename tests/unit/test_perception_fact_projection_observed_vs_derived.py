from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def test_candidate_assertion_does_not_become_truth_without_evidence() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph={
            "entities": [
                {
                    "entity_id": "generic_sparse",
                    "entity_kind": "generic",
                    "confidence": 1.0,
                    "source_root_role": "library_root",
                    "entity_role": "record",
                    "observed_attributes": {
                        "name": {"value": "sparse", "status": "observed", "confidence": 1.0, "evidence_refs": ["name_ref"]}
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

    unsupported = [item for item in result.semantic_assertions if item.canonical_key == "external_signal"][0]
    assert unsupported.fact_kind == "CANDIDATE_FACT"
    assert unsupported.source_kind == "candidate"
    assert unsupported.object_value is None
    assert unsupported.evidence_ids == []
    assert unsupported.truth_eligible is False
    assert unsupported.validation_eligibility is False


def test_missing_observation_stays_unknown_instead_of_false_or_default() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph={
            "entities": [
                {
                    "entity_id": "generic_missing",
                    "entity_kind": "generic",
                    "confidence": 1.0,
                    "source_root_role": "library_root",
                    "entity_role": "record",
                    "observed_attributes": {
                        "name": {"value": "missing", "status": "observed", "confidence": 1.0, "evidence_refs": ["name_ref"]}
                    },
                }
            ]
        },
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["external_signal"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    assertion = result.semantic_assertions[0]
    assert assertion.state in {"UNKNOWN", "INSUFFICIENT_EVIDENCE"}
    assert assertion.object_value is None
    assert assertion.truth_eligible is False
