from aipinho.schemas.artifacts.contract_perception import ObservationCapability
from aipinho.services.artifacts.contract_driven_perception_service import (
    CapabilityRegistry,
    ContractDrivenPerceptionService,
)


def test_source_binding_compile_only_does_not_execute_observer() -> None:
    registry = CapabilityRegistry(
        capabilities=[
            ObservationCapability(
                capability_id="generic_external_observer",
                name="Generic external observer",
                observable_attributes=["external_signal"],
                compatible_entity_kinds=["generic"],
                supported_strategies=["execute_observer"],
                typical_confidence=0.9,
            )
        ]
    )
    service = ContractDrivenPerceptionService(observer_registry=registry)

    def _unexpected_execute(**_: object) -> object:
        raise AssertionError("source binding must not execute observer in compile_only")

    service.observation_boundary.execute = _unexpected_execute  # type: ignore[method-assign]
    result = service.compile(
        graph={
            "entities": [
                {
                    "entity_id": "entity_1",
                    "entity_kind": "generic",
                    "confidence": 1.0,
                    "source_root_role": "library_root",
                    "entity_role": "record",
                    "evidence_refs": ["entity_ref_1"],
                }
            ]
        },
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["external_signal"],
            "perception_compile_policy": {"mode": "compile_only", "execute_observers": False},
        },
    )

    assert result.observation_execution_results == []
    assert result.attribute_observations[0].observation_state in {"missing", "unsupported"}
