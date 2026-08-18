from pathlib import Path

import pytest

from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService


def test_fact_projection_does_not_open_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ContractDrivenPerceptionService()
    graph = {
        "entities": [
            {
                "entity_id": "pathless",
                "entity_kind": "generic",
                "confidence": 1.0,
                "source_root_role": "library_root",
                "entity_role": "record",
                "observed_attributes": {
                    "name": {"value": "pathless", "status": "observed", "confidence": 1.0, "evidence_refs": ["name_ref"]}
                },
            }
        ]
    }

    def _blocked_open(*_: object, **__: object) -> object:
        raise AssertionError("fact projection must not open filesystem")

    monkeypatch.setattr("builtins.open", _blocked_open)
    monkeypatch.setattr(Path, "open", _blocked_open)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    assert result.knowledge_records
    assert result.internal_reason_code is None


def test_fact_projection_does_not_execute_observer_or_relationship_detection() -> None:
    service = ContractDrivenPerceptionService()

    def _fail_relationship_detection(**_: object) -> object:
        raise AssertionError("compile_only fact projection must not detect relationships")

    def _fail_observer(**_: object) -> object:
        raise AssertionError("compile_only fact projection must not execute observers")

    service.relationship_observations = _fail_relationship_detection  # type: ignore[method-assign]
    service.observation_boundary.execute = _fail_observer  # type: ignore[method-assign]
    result = service.compile(
        graph={
            "entities": [
                {
                    "entity_id": "generic",
                    "entity_kind": "generic",
                    "confidence": 1.0,
                    "source_root_role": "library_root",
                    "entity_role": "record",
                    "observed_attributes": {
                        "name": {"value": "generic", "status": "observed", "confidence": 1.0, "evidence_refs": ["name_ref"]}
                    },
                }
            ]
        },
        declared_contract={
            "expected_kind": "generic_collection",
            "expected_schema": ["name"],
            "expected_relationships": [{"relation_kind": "related_to"}],
            "perception_compile_policy": {
                "mode": "compile_only",
                "execute_observers": False,
                "execute_relationship_detection": False,
            },
        },
    )

    assert result.relationship_summary["truth_eligible"] is False
