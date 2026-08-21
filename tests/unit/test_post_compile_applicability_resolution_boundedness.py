from __future__ import annotations

import time
from typing import Any

from aipinho.schemas.artifacts.contract_perception import ObservationCapability, ObservationPlan, ObservationStrategy, ObservationTask
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry
from aipinho.services.artifacts.governed_observation_execution_stage_service import GovernedObservationExecutionStageService, PostCompileObservationBudget
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService


class _FailingApplicabilityAdapter:
    observer_id = "failing_capability"
    version = "1"

    def __init__(self) -> None:
        self.calls = 0

    def applicability_decision(self, **_: Any) -> dict[str, Any]:
        raise RuntimeError("resolver exploded")

    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        self.calls += 1
        return {"observations": []}


class _SlowApplicabilityAdapter(_FailingApplicabilityAdapter):
    observer_id = "failing_capability"

    def applicability_decision(self, **_: Any) -> dict[str, Any]:
        time.sleep(0.01)
        return {"status": "applicable", "reason_code": "TEST_APPLICABLE_AFTER_DELAY"}


def _capability() -> ObservationCapability:
    return ObservationCapability(
        capability_id="failing_capability",
        name="Failing",
        version="1",
        domain="generic",
        observable_attributes=["generic_signal"],
        supported_attribute_names=["generic_signal"],
        compatible_entity_kinds=["file", "*"],
        consumes=["file_path"],
        evidence_types=["generic_evidence"],
        supported_strategies=["execute_observer"],
        observer_binding={"observer_id": "failing_capability", "adapter_id": "failing_capability"},
        available=True,
        status="available",
    )


def _plan() -> ObservationPlan:
    task = ObservationTask(
        goal_id="goal_generic",
        strategy_id="strategy_failing",
        capability_id="failing_capability",
        entity_ref={"entity_ids": ["entity_1"]},
        attribute_name="generic_signal",
        canonical_key="generic_signal",
        inputs={"target_entity_ids": ["entity_1"], "source_ref": "file://one"},
        expected_outputs=["generic_signal"],
        expected_evidence=["generic_evidence"],
        status="PLANNED",
        execution_disposition="deferred_by_compile_policy",
        pre_defer_status="READY_FOR_OBSERVER",
    )
    return ObservationPlan(
        observation_strategies=[
            ObservationStrategy(
                goal_id=task.goal_id,
                strategy_id=str(task.strategy_id),
                strategy_kind="execute_observer",
                attribute_name="generic_signal",
                required_capability_kind="failing_capability",
                rationale="unit test",
            )
        ],
        observation_tasks=[task],
    )


def test_applicability_resolver_failure_blocks_with_governed_reason_and_no_probe() -> None:
    adapter = _FailingApplicabilityAdapter()
    checkpoints: list[tuple[str, dict[str, Any]]] = []
    stage = GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"failing_capability": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[_capability()]),
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )

    result = stage.execute(
        observation_plan=_plan(),
        selected_entities=[{"entity_id": "entity_1", "path": "file://one", "entity_kind": "file"}],
        checkpoint=lambda stage, metrics: checkpoints.append((stage, metrics)),
    )

    assert result.blocked_reason_code == "POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_FAILED"
    assert adapter.calls == 0
    assert result.telemetry["physical_probe_count"] == 0
    assert result.telemetry["capability_applicability_resolution_failure_count"] == 1
    assert "before_physical_probe_dispatch" not in [stage for stage, _ in checkpoints]
    assert checkpoints[-1][0] == "after_post_compile_observation_execution"


def test_applicability_resolution_obeys_total_budget_before_probe() -> None:
    adapter = _SlowApplicabilityAdapter()
    stage = GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"failing_capability": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[_capability()]),
        budget=PostCompileObservationBudget(
            max_total_observation_elapsed_ms=1,
            max_probe_elapsed_ms=500,
            heartbeat_interval_ms=25,
        ),
    )

    result = stage.execute(
        observation_plan=_plan(),
        selected_entities=[{"entity_id": "entity_1", "path": "file://one", "entity_kind": "file"}],
    )

    assert result.blocked_reason_code == "POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED"
    assert adapter.calls == 0
    assert result.telemetry["physical_probe_count"] == 0
    assert result.telemetry["observation_group_planning"]["applicability_started_count"] == 1
