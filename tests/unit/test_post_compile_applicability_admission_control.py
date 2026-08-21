from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.artifacts.contract_perception import (
    EvidenceRecord,
    ObservationCapability,
    ObservationPlan,
    ObservationStrategy,
    ObservationTask,
)
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry
from aipinho.services.artifacts.governed_observation_execution_stage_service import (
    GovernedObservationExecutionStageService,
    PostCompileObservationBudget,
)
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService


class _AdmissionAdapter:
    observer_id = "test_media_capability"
    version = "1"

    def __init__(self, *, supported_extensions: set[str] | None = None) -> None:
        self.supported_extensions = supported_extensions or {"m4a"}
        self.admission_calls = 0
        self.full_resolver_calls = 0
        self.execute_calls: list[ObservationTask] = []

    def applicability_admission_decision(
        self,
        *,
        capability: Any,
        entity: dict[str, Any],
        task: ObservationTask,
        canonical_key: str,
        raw_source_ref: str,
    ) -> dict[str, Any]:
        self.admission_calls += 1
        extension = Path(str(raw_source_ref or "")).suffix.lower().lstrip(".")
        if extension in self.supported_extensions:
            return {
                "status": "applicable",
                "reason_code": "TEST_EXTENSION_DECLARED_BY_BACKEND",
                "evidence": {"extension": extension},
            }
        if extension:
            return {
                "status": "inapplicable",
                "reason_code": "TEST_EXTENSION_NOT_DECLARED_BY_BACKEND",
                "evidence": {"extension": extension},
            }
        return {"status": "unknown", "reason_code": "TEST_EXTENSION_UNKNOWN"}

    def applicability_decision(self, **_: Any) -> dict[str, Any]:
        self.full_resolver_calls += 1
        return {"status": "applicable", "reason_code": "TEST_FULL_RESOLVER_APPLICABLE"}

    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        self.execute_calls.append(task)
        key = str((task.inputs.get("requested_canonical_keys") or ["artist"])[0])
        return {
            "raw_ref": task.inputs.get("file_path"),
            "observations": [
                EvidenceRecord(
                    entity_ref=task.entity_ref,
                    canonical_key=key,
                    attribute_name=key,
                    normalized_value=f"{key}_value",
                    confidence=0.9,
                    capability_id="test_media_capability",
                    observer_id="test_media_capability",
                    raw_ref=task.inputs.get("file_path"),
                ).model_dump(mode="json")
            ],
        }


def _capability() -> ObservationCapability:
    return ObservationCapability(
        capability_id="test_media_capability",
        name="Test media capability",
        version="1",
        domain="media",
        observable_attributes=["artist", "track_title"],
        supported_attribute_names=["artist", "track_title"],
        compatible_entity_kinds=["file", "*"],
        consumes=["file_path"],
        evidence_types=["media_metadata"],
        supported_strategies=["execute_observer"],
        observer_binding={"observer_id": "test_media_capability", "adapter_id": "test_media_capability"},
        available=True,
        status="available",
    )


def _task(canonical_key: str, entity_ids: list[str]) -> ObservationTask:
    return ObservationTask(
        goal_id=f"goal_{canonical_key}",
        strategy_id=f"strategy_{canonical_key}",
        capability_id="test_media_capability",
        entity_ref={"entity_ids": entity_ids},
        attribute_name=canonical_key,
        canonical_key=canonical_key,
        inputs={"target_entity_ids": entity_ids},
        expected_outputs=[canonical_key],
        expected_evidence=["media_metadata"],
        status="PLANNED",
        execution_disposition="deferred_by_compile_policy",
        pre_defer_status="READY_FOR_OBSERVER",
    )


def _plan(tasks: list[ObservationTask]) -> ObservationPlan:
    return ObservationPlan(
        observation_strategies=[
            ObservationStrategy(
                goal_id=task.goal_id,
                strategy_id=str(task.strategy_id),
                strategy_kind="execute_observer",
                attribute_name=task.attribute_name,
                required_capability_kind="test_media_capability",
                rationale="unit test",
            )
            for task in tasks
        ],
        observation_tasks=tasks,
    )


def _stage(adapter: _AdmissionAdapter) -> GovernedObservationExecutionStageService:
    return GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"test_media_capability": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[_capability()]),
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )


def test_admission_partition_avoids_full_resolver_for_unsupported_sources_and_reaches_probe() -> None:
    adapter = _AdmissionAdapter()
    entity_ids = [f"sidecar_{index}" for index in range(40)] + ["track_1"]
    selected_entities = [
        {"entity_id": entity_id, "path": f"library/{entity_id}.lrc", "entity_kind": "file"}
        for entity_id in entity_ids[:-1]
    ] + [{"entity_id": "track_1", "path": "library/song.m4a", "entity_kind": "file"}]
    checkpoints: list[str] = []

    result = _stage(adapter).execute(
        observation_plan=_plan([_task("artist", entity_ids), _task("track_title", entity_ids)]),
        selected_entities=selected_entities,
        checkpoint=lambda stage, metrics: checkpoints.append(stage),
    )

    planning = result.telemetry["observation_group_planning"]
    assert result.blocked_reason_code is None
    assert adapter.full_resolver_calls == 0
    assert adapter.admission_calls == 82
    assert len(adapter.execute_calls) == 1
    assert result.telemetry["dedup_group_count"] == 1
    assert result.telemetry["physical_probe_count"] == 1
    assert result.telemetry["expected_inapplicable_candidate_count"] == 80
    assert result.telemetry["eligible_candidate_count"] == 2
    assert result.telemetry["resolver_calls_avoided_by_admission"] == 82
    assert planning["target_entity_ref_count"] == 82
    assert planning["target_entity_ref_count"] == (
        planning["eligible_candidate_count"]
        + planning["expected_inapplicable_candidate_count"]
        + planning["unknown_candidate_count"]
        + planning["malformed_or_missing_source_ref_count"]
        + planning["skipped_or_deferred_candidate_count"]
    )
    assert result.telemetry["systemic_execution_failure_count"] == 0
    assert "before_physical_probe_dispatch" in checkpoints


def test_no_eligible_admission_blocks_precisely_without_probe_or_false_success() -> None:
    adapter = _AdmissionAdapter()
    entity_ids = [f"sidecar_{index}" for index in range(5001)]
    selected_entities = [
        {"entity_id": entity_id, "path": f"library/{entity_id}.lrc", "entity_kind": "file"}
        for entity_id in entity_ids
    ]

    result = _stage(adapter).execute(
        observation_plan=_plan([_task("artist", entity_ids)]),
        selected_entities=selected_entities,
    )

    assert result.blocked_reason_code == "POST_COMPILE_APPLICABILITY_TARGET_EXPANSION_EXCEEDED"
    assert result.telemetry["physical_probe_count"] == 0
    assert result.telemetry["files_attempted"] == 0
    assert result.telemetry["expected_inapplicable_candidate_count"] == 5000
    assert result.telemetry["capability_inapplicable_count"] == 5000
    assert result.telemetry["max_applicability_admission_candidate_count"] == 5000
    assert result.telemetry["groups_created_count"] == 0
    assert result.telemetry["results_rejected_by_policy"] == 1
    assert adapter.execute_calls == []


def test_extension_admission_is_routing_evidence_not_semantic_truth() -> None:
    adapter = _AdmissionAdapter()
    result = _stage(adapter).execute(
        observation_plan=_plan([_task("artist", ["track_1"])]),
        selected_entities=[{"entity_id": "track_1", "path": "library/song.m4a", "entity_kind": "file"}],
    )

    assert result.telemetry["physical_probe_count"] == 1
    record = result.observation_execution_results[0].evidence_set.records[0]
    assert record.canonical_key == "artist"
    assert record.normalized_value == "artist_value"
    assert record.canonical_key not in {"extension", "container", "codec"}
