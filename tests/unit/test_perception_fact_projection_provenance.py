from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def test_observed_fact_preserves_evidence_and_provenance_refs() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph={
            "entities": [
                {
                    "entity_id": "generic_observed",
                    "entity_kind": "generic",
                    "confidence": 1.0,
                    "source_root_role": "library_root",
                    "entity_role": "record",
                    "evidence_refs": ["entity_ref_1"],
                    "observed_attributes": {
                        "name": {
                            "value": "observed value",
                            "status": "observed",
                            "confidence": 0.97,
                            "evidence_refs": ["attribute_ref_1"],
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

    knowledge = result.knowledge_records[0]
    assertion = result.semantic_assertions[0]
    assert knowledge.fact_kind == "OBSERVED_FACT"
    assert knowledge.source_kind == "observed"
    assert knowledge.evidence_ids
    assert knowledge.provenance_refs
    assert assertion.fact_kind == "OBSERVED_FACT"
    assert assertion.source_kind == "observed"
    assert assertion.provenance_refs
    assert assertion.truth_eligible is True


def test_derived_fact_keeps_derivation_provenance_without_claiming_observation_origin() -> None:
    result = ContractDrivenPerceptionService().compile(
        graph={
            "entities": [
                {
                    "entity_id": "generic_file",
                    "entity_kind": "file",
                    "confidence": 1.0,
                    "source_root_role": "library_root",
                    "entity_role": "asset",
                    "evidence_refs": ["entity_ref_2"],
                    "observed_attributes": {
                        "name": {
                            "value": "generic.asset",
                            "status": "observed",
                            "confidence": 1.0,
                            "evidence_refs": ["name_ref_2"],
                        }
                    },
                }
            ]
        },
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["extension"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    knowledge = result.knowledge_records[0]
    assertion = result.semantic_assertions[0]
    assert knowledge.fact_kind == "DERIVED_FACT"
    assert knowledge.source_kind == "derived"
    assert knowledge.derivation_rule == "derive_from_path"
    assert assertion.fact_kind == "DERIVED_FACT"
    assert assertion.source_kind == "derived"
    assert assertion.derivation_rule == "contract_assertion_from_derived_knowledge"
