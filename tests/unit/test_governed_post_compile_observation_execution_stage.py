from __future__ import annotations

import time
import threading
from typing import Any

from aipinho.schemas.artifacts.contract_perception import (
    ObservationCapability,
    ObservationPlan,
    ObservationStrategy,
    ObservationTask,
)
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry, ContractDrivenPerceptionService
from aipinho.services.artifacts.governed_observation_execution_stage_service import (
    GovernedObservationExecutionStageService,
    PostCompileObservationBudget,
)
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService


class _Adapter:
    observer_id = "media_metadata_reader"
    version = "1"

    def __init__(self, *, delay_s: float = 0.0, keys: list[str] | None = None) -> None:
        self.delay_s = delay_s
        self.keys = keys or ["track_title", "artist"]
        self.calls: list[ObservationTask] = []
        self._lock = threading.Lock()
        self.active_calls = 0
        self.max_active_calls = 0

    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        with self._lock:
            self.calls.append(task)
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            if self.delay_s:
                time.sleep(self.delay_s)
            return {
                "raw_ref": task.inputs.get("file_path"),
                "observations": [
                    {
                        "entity_ref": task.entity_ref,
                        "attribute_name": key,
                        "canonical_key": key,
                        "normalized_value": f"{key}_value",
                        "confidence": 0.9,
                        "raw_ref": task.inputs.get("file_path"),
                    }
                    for key in self.keys
                ],
            }
        finally:
            with self._lock:
                self.active_calls -= 1


def _capability(*, available: bool = True, status: str = "available") -> ObservationCapability:
    return ObservationCapability(
        capability_id="media_metadata_reader",
        name="Media metadata reader",
        version="1",
        domain="media_metadata",
        observable_attributes=["track_title", "artist", "album", "album_artist"],
        supported_attribute_names=["track_title", "artist", "album", "album_artist"],
        compatible_entity_kinds=["file", "media_asset_candidate", "*"],
        evidence_types=["media_metadata_evidence"],
        supported_strategies=["execute_observer"],
        typical_confidence=0.9,
        observer_binding={
            "observer_id": "media_metadata_reader",
            "adapter_id": "media_metadata_reader",
            "input_schema": {"required": ["file_path"]},
        },
        available=available,
        status=status,
    )


def _task(attribute: str, *, entity_id: str = "entity_1", source_ref: str = "media://one") -> ObservationTask:
    return ObservationTask(
        goal_id=f"goal_{attribute}_{entity_id}_{source_ref}",
        strategy_id="strategy_media",
        capability_id="media_metadata_reader",
        entity_ref={"entity_ids": [entity_id]},
        attribute_name=attribute,
        canonical_key=attribute,
        inputs={"target_entity_ids": [entity_id], "source_ref": source_ref, "required_confidence": 0.7},
        expected_outputs=[attribute],
        expected_evidence=["media_metadata_evidence"],
        status="PLANNED",
        execution_disposition="deferred_by_compile_policy",
        pre_defer_status="READY_FOR_OBSERVER",
    )


def _plan(tasks: list[ObservationTask]) -> ObservationPlan:
    return ObservationPlan(
        observation_strategies=[
            ObservationStrategy(
                goal_id="goal",
                strategy_id="strategy_media",
                strategy_kind="execute_observer",
                attribute_name="track_title",
                required_capability_kind="media_metadata",
                rationale="unit test",
            )
        ],
        observation_tasks=tasks,
    )


def _stage(adapter: _Adapter, *, budget: PostCompileObservationBudget | None = None) -> GovernedObservationExecutionStageService:
    return GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"media_metadata_reader": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[_capability()]),
        budget=budget or PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )


def _stage_with_capability(
    adapter: _Adapter,
    *,
    capability: ObservationCapability,
    budget: PostCompileObservationBudget | None = None,
) -> GovernedObservationExecutionStageService:
    return GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"media_metadata_reader": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[capability]),
        budget=budget or PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )


def test_one_entity_many_tasks_create_one_physical_probe_and_logical_fanout() -> None:
    adapter = _Adapter(keys=["track_title", "artist"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([_task("track_title"), _task("artist"), _task("album_artist")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert len(adapter.calls) == 1
    assert len(result.observation_execution_results) == 1
    assert result.telemetry["physical_probe_count"] == 1
    assert result.telemetry["files_attempted"] == 1
    assert result.telemetry["files_succeeded"] == 1
    assert result.telemetry["goals_satisfied"] == 2
    assert result.telemetry["goals_unsatisfied"] == 1
    assert result.telemetry["evidence_records_created"] == 2


def test_source_ref_and_entity_id_are_part_of_physical_dedup_key() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id="entity_1", source_ref="media://one"),
            _task("artist", entity_id="entity_1", source_ref="media://two"),
            _task("artist", entity_id="entity_2", source_ref="media://one"),
        ]),
        selected_entities=[
            {"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"},
            {"entity_id": "entity_2", "path": "media://one", "entity_role": "media_asset_candidate"},
        ],
    )

    assert len(adapter.calls) == 3
    assert [call.inputs["file_path"] for call in adapter.calls] == ["media://one", "media://two", "media://one"]
    assert result.telemetry["dedup_group_count"] == 3
    assert result.telemetry["physical_probe_count"] == 3


def test_arbitrary_planned_task_is_not_executed_without_defer_marker() -> None:
    adapter = _Adapter(keys=["artist"])
    task = _task("artist")
    task = task.model_copy(update={"execution_disposition": None, "pre_defer_status": None})

    result = _stage(adapter).execute(
        observation_plan=_plan([task]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one"}],
    )

    assert adapter.calls == []
    assert result.telemetry["dedup_group_count"] == 0
    assert result.telemetry["files_attempted"] == 0


def test_timeout_quarantines_late_result_and_fail_stops_before_next_probe() -> None:
    adapter = _Adapter(delay_s=0.2, keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=20, heartbeat_interval_ms=5, max_consecutive_execution_failures=1),
    )
    checkpoints: list[str] = []

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id="entity_1", source_ref="media://one"),
            _task("artist", entity_id="entity_2", source_ref="media://two"),
        ]),
        selected_entities=[
            {"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"},
            {"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"},
        ],
        checkpoint=lambda stage, metrics: checkpoints.append(stage),
    )

    assert len(adapter.calls) == 1
    assert result.blocked_reason_code == "POST_COMPILE_PHYSICAL_PROBE_TIMEOUT"
    assert result.telemetry["physical_probe_count"] == 1
    assert result.observation_execution_results[0].status == "BLOCKED_TIMEOUT"
    assert result.observation_execution_results[0].evidence_set.records == []
    assert "physical_probe_checkpoint" in checkpoints
    time.sleep(0.25)
    stage.execute(observation_plan=_plan([]), selected_entities=[])


def test_cross_run_quarantine_bound_blocks_second_run_without_new_probe() -> None:
    adapter = _Adapter(delay_s=0.2, keys=["artist"])
    budget = PostCompileObservationBudget(max_probe_elapsed_ms=20, heartbeat_interval_ms=5, max_quarantined_workers=1)
    stage_a = _stage(adapter, budget=budget)
    stage_b = _stage(adapter, budget=budget)

    first = stage_a.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )
    second = stage_b.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_2", source_ref="media://two")]),
        selected_entities=[{"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"}],
    )

    assert first.blocked_reason_code == "POST_COMPILE_PHYSICAL_PROBE_TIMEOUT"
    assert second.blocked_reason_code == "POST_COMPILE_OBSERVATION_QUARANTINE_BOUND_OCCUPIED"
    assert len(adapter.calls) == 1
    assert second.telemetry["physical_probe_count"] == 0
    assert second.telemetry["files_attempted"] == 0
    time.sleep(0.25)
    stage_b.execute(observation_plan=_plan([]), selected_entities=[])


def test_concurrent_runs_cannot_exceed_atomic_worker_bound() -> None:
    adapter = _Adapter(delay_s=0.15, keys=["artist"])
    budget = PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=5, max_quarantined_workers=1)
    stages = [_stage(adapter, budget=budget), _stage(adapter, budget=budget)]
    barrier = threading.Barrier(3)
    results: list[Any] = []

    def run(stage: GovernedObservationExecutionStageService, entity_id: str, source_ref: str) -> None:
        barrier.wait()
        results.append(
            stage.execute(
                observation_plan=_plan([_task("artist", entity_id=entity_id, source_ref=source_ref)]),
                selected_entities=[{"entity_id": entity_id, "path": source_ref, "entity_role": "media_asset_candidate"}],
            )
        )

    threads = [
        threading.Thread(target=run, args=(stages[0], "entity_1", "media://one")),
        threading.Thread(target=run, args=(stages[1], "entity_2", "media://two")),
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert len(adapter.calls) == 1
    assert adapter.max_active_calls == 1
    assert sorted(result.blocked_reason_code or "" for result in results) == [
        "",
        "POST_COMPILE_OBSERVATION_WORKER_BOUND_OCCUPIED",
    ]
    blocked = next(result for result in results if result.blocked_reason_code)
    assert blocked.telemetry["physical_probe_count"] == 0
    assert blocked.telemetry["files_attempted"] == 0


def test_total_observation_deadline_blocks_active_probe_before_probe_deadline() -> None:
    adapter = _Adapter(delay_s=0.1, keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, max_total_observation_elapsed_ms=20, heartbeat_interval_ms=5),
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert result.blocked_reason_code == "POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED"
    assert len(adapter.calls) == 1
    assert result.observation_execution_results[0].evidence_set.records == []
    time.sleep(0.12)
    stage.execute(observation_plan=_plan([]), selected_entities=[])


def test_materialized_observation_bytes_budget_blocks_before_materialization() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=10, max_materialized_observation_bytes=10),
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert result.blocked_reason_code == "POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED"
    assert result.observation_execution_results[0].status == "BLOCKED_POLICY"
    assert result.observation_execution_results[0].evidence_set.records == []
    assert result.telemetry["physical_probe_count"] == 1
    assert result.telemetry["files_failed"] == 1


def test_evidence_record_budget_replaces_over_budget_result_before_materialization() -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=10, max_evidence_records=1),
    )
    selected_entities = [
        {"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"},
        {"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"},
    ]
    perception = service.compile(
        graph={"entities": selected_entities},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["artist"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    execution = stage.execute(observation_plan=perception.observation_plan, selected_entities=selected_entities)
    materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=execution.observation_execution_results,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["artist"]},
    )

    assert execution.blocked_reason_code == "POST_COMPILE_OBSERVATION_EVIDENCE_RECORD_BUDGET_EXCEEDED"
    assert [len(result.evidence_set.records) for result in execution.observation_execution_results] == [1, 0]
    observed_entity_ids = {
        item.entity_id
        for item in materialized.attribute_observations
        if item.canonical_key == "artist" and item.observation_state == "observed"
    }
    assert observed_entity_ids == {"entity_1"}


def test_zero_consecutive_failure_limit_does_not_block_success() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=10, max_consecutive_execution_failures=0),
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert result.blocked_reason_code is None
    assert result.telemetry["files_succeeded"] == 1


def test_unavailable_capability_is_revalidated_before_physical_execution() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage_with_capability(adapter, capability=_capability(available=False, status="unavailable"))

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert adapter.calls == []
    assert result.telemetry["dedup_group_count"] == 0
    assert result.telemetry["physical_probe_count"] == 0


def test_post_execution_materialization_updates_evidence_and_attribute_observations() -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    adapter = _Adapter(keys=["artist"])
    stage = _stage(adapter)
    selected_entities = [{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}]
    perception = service.compile(
        graph={"entities": selected_entities},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["artist"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    execution = stage.execute(observation_plan=perception.observation_plan, selected_entities=selected_entities)
    materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=execution.observation_execution_results,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["artist"]},
    )

    assert perception.observation_execution_results == []
    assert materialized.observation_execution_results
    assert any(record.canonical_key == "artist" for record in materialized.evidence_set.records)
    assert any(item.canonical_key == "artist" and item.observation_state == "observed" for item in materialized.attribute_observations)
    physical_tasks = {
        item.canonical_key: item
        for item in materialized.observation_plan.observation_tasks
        if item.execution_disposition == "executed_by_post_compile_stage"
    }
    assert physical_tasks["artist"].status == "EXECUTED"
    assert physical_tasks["artist"].created_from["logical_claim_satisfaction_not_inferred"] is True
