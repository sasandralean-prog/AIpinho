from __future__ import annotations

from typing import Any

from aipinho.schemas.artifacts.contract_perception import (
    EvidenceRecord,
    ObservationCapability,
    ObservationPlan,
    ObservationStrategy,
    ObservationTask,
)
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry
from aipinho.services.artifacts.governed_observation_execution_stage_service import GovernedObservationExecutionStageService, PostCompileObservationBudget
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService


class _Adapter:
    observer_id = "generic_capability"
    version = "1"

    def __init__(self, *, applicability: str = "applicable") -> None:
        self.applicability = applicability
        self.calls = 0

    def applicability_decision(
        self,
        *,
        capability: Any,
        entity: dict[str, Any],
        task: ObservationTask,
        canonical_key: str,
        raw_source_ref: str,
    ) -> dict[str, Any]:
        return {"status": self.applicability, "reason_code": f"TEST_{self.applicability.upper()}"}

    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        self.calls += 1
        return {
            "raw_ref": task.inputs.get("source_ref"),
            "observations": [
                EvidenceRecord(
                    entity_ref={"entity_id": "entity_1"},
                    canonical_key="generic_signal",
                    attribute_name="generic_signal",
                    normalized_value="observed",
                    confidence=0.9,
                    capability_id="generic_capability",
                    observer_id="generic_capability",
                    raw_ref=task.inputs.get("source_ref"),
                ).model_dump(mode="json")
            ],
        }


def _capability() -> ObservationCapability:
    return ObservationCapability(
        capability_id="generic_capability",
        name="Generic",
        version="1",
        domain="generic",
        observable_attributes=["generic_signal"],
        supported_attribute_names=["generic_signal"],
        compatible_entity_kinds=["file", "*"],
        consumes=["file_path"],
        evidence_types=["generic_evidence"],
        supported_strategies=["execute_observer"],
        observer_binding={"observer_id": "generic_capability", "adapter_id": "generic_capability"},
        available=True,
        status="available",
    )


def _task() -> ObservationTask:
    return ObservationTask(
        goal_id="goal_generic",
        strategy_id="strategy_generic",
        capability_id="generic_capability",
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


def _plan() -> ObservationPlan:
    return ObservationPlan(
        observation_strategies=[
            ObservationStrategy(
                goal_id="goal_generic",
                strategy_id="strategy_generic",
                strategy_kind="execute_observer",
                attribute_name="generic_signal",
                required_capability_kind="generic_capability",
                rationale="unit test",
            )
        ],
        observation_tasks=[_task()],
    )


def _stage(adapter: _Adapter) -> GovernedObservationExecutionStageService:
    return GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"generic_capability": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[_capability()]),
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )


def test_execute_emits_bounded_group_planning_checkpoints() -> None:
    checkpoints: list[tuple[str, dict[str, Any]]] = []

    result = _stage(_Adapter()).execute(
        observation_plan=_plan(),
        selected_entities=[{"entity_id": "entity_1", "path": "file://one", "entity_kind": "file"}],
        checkpoint=lambda stage, metrics: checkpoints.append((stage, metrics)),
    )

    stages = [stage for stage, _ in checkpoints]
    assert result.blocked_reason_code is None
    assert "before_observation_physical_group_planning" in stages
    assert "observation_task_scan_checkpoint" in stages
    assert "before_capability_applicability_resolution" in stages
    assert "after_capability_applicability_resolution" in stages
    assert "after_observation_physical_group_planning" in stages
    assert "before_backend_availability_snapshot" in stages
    assert "after_backend_availability_snapshot" in stages
    assert "before_physical_probe_dispatch" in stages

    planning = dict(checkpoints[stages.index("after_observation_physical_group_planning")][1])
    assert planning["dedup_group_count"] == 1
    assert planning["observation_group_planning"]["tasks_seen"] == 1
    assert "entities" not in planning
    assert "selected_entities" not in planning

