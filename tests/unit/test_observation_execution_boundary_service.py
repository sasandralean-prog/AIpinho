from __future__ import annotations

import time
from typing import Any

from aipinho.schemas.artifacts.contract_perception import (
    ObservationCapability,
    ObservationExecutionPolicy,
    ObservationTask,
)
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService


class MockObserverAdapter:
    observer_id = "mock_observer"
    version = "1"

    def __init__(self, payload: dict[str, Any] | None = None, *, delay_s: float = 0.0, raises: Exception | None = None) -> None:
        self.payload = payload if payload is not None else {
            "raw_ref": "mock://observation/1",
            "observations": [
                {
                    "attribute_name": "generic_signal",
                    "canonical_key": "generic_signal",
                    "normalized_value": "observed",
                    "confidence": 0.91,
                    "raw_ref": "mock://observation/1",
                    "provenance": {"source": "mock_adapter"},
                }
            ],
        }
        self.delay_s = delay_s
        self.raises = raises
        self.calls: list[tuple[ObservationTask, object]] = []

    def execute(self, task: ObservationTask, binding) -> dict[str, Any]:
        self.calls.append((task, binding))
        if self.delay_s:
            time.sleep(self.delay_s)
        if self.raises:
            raise self.raises
        return self.payload


def _task(**updates: Any) -> ObservationTask:
    data = {
        "goal_id": "goal_generic_signal",
        "strategy_id": "strategy_execute_observer",
        "capability_id": "generic_signal_observer",
        "entity_ref": {"entity_id": "entity_1"},
        "attribute_name": "generic_signal",
        "canonical_key": "generic_signal",
        "inputs": {"entity_ref": {"entity_id": "entity_1"}, "required_confidence": 0.5},
        "expected_outputs": ["generic_signal"],
        "expected_evidence": ["structured_attribute_evidence"],
        "status": "READY_FOR_OBSERVER",
    }
    data.update(updates)
    return ObservationTask(**data)


def _capability(**updates: Any) -> ObservationCapability:
    data = {
        "capability_id": "generic_signal_observer",
        "name": "Generic signal observer",
        "version": "1",
        "domain": "generic",
        "produces": ["generic_signal"],
        "consumes": ["entity_ref"],
        "observable_attributes": ["generic_signal"],
        "supported_attribute_names": ["generic_signal"],
        "compatible_entity_kinds": ["file"],
        "supported_entity_types": ["file"],
        "evidence_types": ["structured_attribute_evidence"],
        "supported_strategies": ["execute_observer"],
        "typical_confidence": 0.9,
        "observer_binding": {
            "observer_id": "mock_observer",
            "adapter_id": "mock_observer",
            "version": "1",
            "input_schema": {"required": ["entity_ref"]},
            "output_schema": {"required": ["observations"]},
            "acquisition_method": "execute_observer",
        },
        "status": "available",
    }
    data.update(updates)
    return ObservationCapability(**data)


def test_observation_task_ready_for_observer_executes_via_boundary_and_produces_evidence() -> None:
    adapter = MockObserverAdapter()
    boundary = ObservationExecutionBoundaryService(adapters={"mock_observer": adapter})

    result = boundary.execute(task=_task(), capability=_capability())

    assert result.status == "EXECUTED"
    assert result.errors == []
    assert result.evidence_set.records
    record = result.evidence_set.records[0]
    assert record.observer_id == "mock_observer"
    assert record.capability_id == "generic_signal_observer"
    assert record.raw_ref == "mock://observation/1"
    assert record.provenance["boundary"] == "ObservationExecutionBoundaryService"
    assert record.normalized_value == "observed"
    assert adapter.calls


def test_observer_timeout_generates_typed_error_without_valid_evidence() -> None:
    adapter = MockObserverAdapter(delay_s=0.02)
    boundary = ObservationExecutionBoundaryService(adapters={"mock_observer": adapter})

    result = boundary.execute(
        task=_task(),
        capability=_capability(observer_binding={**_capability().observer_binding, "timeout_ms": 1}),
        policy=ObservationExecutionPolicy(timeout_ms=1),
    )

    assert result.status == "BLOCKED_TIMEOUT"
    assert result.errors[0].code == "OBSERVER_TIMEOUT"
    assert result.evidence_set.records == []


def test_invalid_observer_output_does_not_generate_valid_evidence() -> None:
    adapter = MockObserverAdapter(payload={"raw_ref": "mock://bad"})
    boundary = ObservationExecutionBoundaryService(adapters={"mock_observer": adapter})

    result = boundary.execute(task=_task(), capability=_capability())

    assert result.status == "FAILED"
    assert result.errors[0].code == "OBSERVER_OUTPUT_SCHEMA_INVALID"
    assert result.evidence_set.records == []


def test_policy_blocked_prevents_observer_execution() -> None:
    adapter = MockObserverAdapter()
    boundary = ObservationExecutionBoundaryService(adapters={"mock_observer": adapter})

    result = boundary.execute(
        task=_task(),
        capability=_capability(),
        policy=ObservationExecutionPolicy(allow_execution=False, reason="unit_test_policy_block"),
    )

    assert result.status == "BLOCKED_POLICY"
    assert result.errors[0].code == "OBSERVER_POLICY_BLOCKED"
    assert result.evidence_set.records == []
    assert adapter.calls == []


def test_unbound_observer_reports_observer_not_bound() -> None:
    boundary = ObservationExecutionBoundaryService(adapters={})

    result = boundary.execute(task=_task(), capability=_capability(observer_binding={}))

    assert result.status == "BLOCKED_OBSERVER_ERROR"
    assert result.errors[0].code == "OBSERVER_NOT_BOUND"
    assert result.evidence_set.records == []


def test_low_confidence_output_is_rejected_as_invalid_evidence_for_contract() -> None:
    adapter = MockObserverAdapter(
        payload={
            "observations": [
                {
                    "attribute_name": "generic_signal",
                    "canonical_key": "generic_signal",
                    "normalized_value": "weak",
                    "confidence": 0.2,
                }
            ]
        }
    )
    boundary = ObservationExecutionBoundaryService(adapters={"mock_observer": adapter})

    result = boundary.execute(task=_task(inputs={"entity_ref": {"entity_id": "entity_1"}, "required_confidence": 0.8}), capability=_capability())

    assert result.status == "FAILED"
    assert result.errors[0].code == "OBSERVER_CONFIDENCE_TOO_LOW"
    assert result.evidence_set.records == []
