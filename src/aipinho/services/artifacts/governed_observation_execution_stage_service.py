from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from aipinho.capabilities.media_metadata.descriptor import MEDIA_METADATA_EVIDENCE_KEYS
from aipinho.schemas.artifacts.contract_perception import (
    EvidenceSet,
    ObservationCapability,
    ObservationExecutionError,
    ObservationExecutionPolicy,
    ObservationExecutionResult,
    ObservationExecutionTimelineEvent,
    ObservationPlan,
    ObservationTask,
)
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService


@dataclass(frozen=True)
class PostCompileObservationBudget:
    max_physical_probes: int = 2500
    max_probe_elapsed_ms: int = 15000
    max_total_observation_elapsed_ms: int = 120000
    max_evidence_records: int = 250000
    max_consecutive_execution_failures: int = 10
    max_materialized_observation_bytes: int = 8_000_000
    heartbeat_interval_ms: int = 1000


@dataclass(frozen=True)
class PhysicalObservationGroup:
    physical_probe_key: tuple[str, str, str]
    entity_id: str
    capability_id: str
    normalized_source_ref: str
    entity: dict[str, Any]
    tasks: list[ObservationTask] = field(default_factory=list)

    @property
    def requested_canonical_keys(self) -> list[str]:
        return sorted({
            str(task.canonical_key or task.attribute_name)
            for task in self.tasks
            if str(task.canonical_key or task.attribute_name or "").strip()
        })


@dataclass(frozen=True)
class GovernedObservationExecutionStageResult:
    observation_execution_results: list[ObservationExecutionResult]
    telemetry: dict[str, Any]
    physical_groups: list[PhysicalObservationGroup]
    blocked_reason_code: str | None = None


class GovernedObservationExecutionStageService:
    """Runs deferred observer tasks after compile without becoming a truth authority."""

    def __init__(
        self,
        *,
        observation_boundary: ObservationExecutionBoundaryService,
        observer_registry: Any,
        budget: PostCompileObservationBudget | None = None,
    ) -> None:
        self.observation_boundary = observation_boundary
        self.observer_registry = observer_registry
        self.budget = budget or PostCompileObservationBudget()

    def execute(
        self,
        *,
        observation_plan: ObservationPlan,
        selected_entities: list[dict[str, Any]],
        checkpoint: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GovernedObservationExecutionStageResult:
        started = time.monotonic()
        self._checkpoint(checkpoint, "before_post_compile_observation_execution", {})
        groups = self._physical_groups(observation_plan=observation_plan, selected_entities=selected_entities)
        self._checkpoint(
            checkpoint,
            "after_observation_task_grouping",
            self._grouping_metrics(groups=groups),
        )
        results: list[ObservationExecutionResult] = []
        consecutive_failures = 0
        blocked_reason: str | None = None
        evidence_records_created = 0
        for index, group in enumerate(groups, start=1):
            if index > self.budget.max_physical_probes:
                blocked_reason = "POST_COMPILE_OBSERVATION_PHYSICAL_PROBE_BUDGET_EXCEEDED"
                break
            if (time.monotonic() - started) * 1000 > self.budget.max_total_observation_elapsed_ms:
                blocked_reason = "POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED"
                break
            self._checkpoint(
                checkpoint,
                "before_physical_probe",
                {**self._group_metrics(group), "physical_probe_index": index},
            )
            result, timed_out = self._execute_group(group=group, checkpoint=checkpoint, stage_started=started)
            results.append(result)
            record_count = len(getattr(result.evidence_set, "records", []) or [])
            evidence_records_created += record_count
            if evidence_records_created > self.budget.max_evidence_records:
                blocked_reason = "POST_COMPILE_OBSERVATION_EVIDENCE_RECORD_BUDGET_EXCEEDED"
                break
            if result.status == "EXECUTED" and record_count > 0:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
            self._checkpoint(
                checkpoint,
                "after_physical_probe",
                {
                    **self._group_metrics(group),
                    "physical_probe_index": index,
                    "physical_probe_status": result.status,
                    "evidence_record_count": record_count,
                },
            )
            if timed_out:
                blocked_reason = "POST_COMPILE_PHYSICAL_PROBE_TIMEOUT"
                break
            if consecutive_failures > self.budget.max_consecutive_execution_failures:
                blocked_reason = "POST_COMPILE_OBSERVATION_CONSECUTIVE_EXECUTION_FAILURES_EXCEEDED"
                break
        fanout = self._fanout_metrics(groups=groups, results=results)
        telemetry = {
            **self._grouping_metrics(groups=groups),
            **fanout,
            "physical_probe_count": len(results),
            "files_attempted": len(results),
            "files_succeeded": len([
                item for item in results if item.status == "EXECUTED" and len(item.evidence_set.records) > 0
            ]),
            "files_failed": len([
                item for item in results if not (item.status == "EXECUTED" and len(item.evidence_set.records) > 0)
            ]),
            "evidence_records_created": evidence_records_created,
            "execution_status": "blocked" if blocked_reason else "executed" if results else "not_started",
            "blocked_reason_code": blocked_reason,
        }
        self._checkpoint(checkpoint, "after_evidence_fanout", telemetry)
        self._checkpoint(checkpoint, "after_post_compile_observation_execution", telemetry)
        return GovernedObservationExecutionStageResult(
            observation_execution_results=results,
            telemetry=telemetry,
            physical_groups=groups,
            blocked_reason_code=blocked_reason,
        )

    def _physical_groups(
        self,
        *,
        observation_plan: ObservationPlan,
        selected_entities: list[dict[str, Any]],
    ) -> list[PhysicalObservationGroup]:
        entities_by_id = {str(entity.get("entity_id") or ""): entity for entity in selected_entities}
        strategies_by_id = {item.strategy_id: item for item in observation_plan.observation_strategies}
        groups: dict[tuple[str, str, str], PhysicalObservationGroup] = {}
        for task in observation_plan.observation_tasks:
            if not self._is_deferred_executable_task(task):
                continue
            strategy = strategies_by_id.get(str(task.strategy_id or ""))
            if strategy is None or strategy.strategy_kind != "execute_observer":
                continue
            capability_id = str(task.capability_id or "")
            if not capability_id or self.observer_registry.get(capability_id) is None:
                continue
            for entity_id in self._target_entity_ids(task):
                entity = entities_by_id.get(entity_id)
                if entity is None:
                    continue
                source_ref = self._normalized_source_ref(task=task, entity=entity)
                key = (entity_id, capability_id, source_ref)
                group = groups.get(key)
                if group is None:
                    group = PhysicalObservationGroup(
                        physical_probe_key=key,
                        entity_id=entity_id,
                        capability_id=capability_id,
                        normalized_source_ref=source_ref,
                        entity=entity,
                        tasks=[],
                    )
                    groups[key] = group
                group.tasks.append(task)
        return list(groups.values())

    def _execute_group(
        self,
        *,
        group: PhysicalObservationGroup,
        checkpoint: Callable[[str, dict[str, Any]], None] | None,
        stage_started: float,
    ) -> tuple[ObservationExecutionResult, bool]:
        task = self._execution_task_for_group(group)
        capability = self.observer_registry.get(group.capability_id)
        policy = ObservationExecutionPolicy(timeout_ms=self.budget.max_probe_elapsed_ms)
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aipinho_observer_probe")
        future: Future[ObservationExecutionResult] = executor.submit(
            self.observation_boundary.execute,
            task=task,
            capability=capability,
            policy=policy,
        )
        deadline = time.monotonic() + (self.budget.max_probe_elapsed_ms / 1000)
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                wait_seconds = min(max(0.001, remaining), max(0.001, self.budget.heartbeat_interval_ms / 1000))
                try:
                    result = future.result(timeout=wait_seconds)
                    executor.shutdown(wait=False, cancel_futures=True)
                    return self._with_physical_provenance(result, group=group), False
                except TimeoutError:
                    self._checkpoint(
                        checkpoint,
                        "physical_probe_checkpoint",
                        {
                            **self._group_metrics(group),
                            "elapsed_ms": round((time.monotonic() - stage_started) * 1000, 3),
                            "probe_elapsed_ms": round((self.budget.max_probe_elapsed_ms / 1000 - max(0.0, remaining)) * 1000, 3),
                        },
                    )
            future.cancel()
            timeout_result = self._timeout_result(task=task, capability=capability, group=group)
            executor.shutdown(wait=False, cancel_futures=True)
            return timeout_result, True
        except Exception as exc:
            executor.shutdown(wait=False, cancel_futures=True)
            return self._runtime_error_result(task=task, capability=capability, group=group, exc=exc), False

    def _execution_task_for_group(self, group: PhysicalObservationGroup) -> ObservationTask:
        first = group.tasks[0]
        entity_ref = self._execution_entity_ref(entity=group.entity, capability_id=group.capability_id)
        source_ref = self._source_ref_for_entity(group.entity)
        expected_outputs = sorted(MEDIA_METADATA_EVIDENCE_KEYS) if group.capability_id == "media_metadata_reader" else group.requested_canonical_keys
        return first.model_copy(
            update={
                "status": "READY_FOR_OBSERVER",
                "entity_ref": entity_ref,
                "inputs": {
                    **dict(first.inputs or {}),
                    "entity_id": group.entity_id,
                    "file_path": source_ref,
                    "source_ref": group.normalized_source_ref,
                    "entity_role": entity_ref.get("entity_role"),
                    "source_root_role": entity_ref.get("source_root_role"),
                    "required_confidence": first.inputs.get("required_confidence", 0.0),
                },
                "expected_outputs": expected_outputs,
                "created_from": {
                    **dict(first.created_from or {}),
                    "physical_probe_key": list(group.physical_probe_key),
                    "grouped_observation_task_ids": [task.observation_task_id for task in group.tasks],
                    "grouped_goal_ids": [task.goal_id for task in group.tasks],
                    "requested_canonical_keys": group.requested_canonical_keys,
                },
            }
        )

    def _with_physical_provenance(self, result: ObservationExecutionResult, *, group: PhysicalObservationGroup) -> ObservationExecutionResult:
        provenance = dict(result.provenance or {})
        provenance.update(
            {
                "physical_probe_key": list(group.physical_probe_key),
                "grouped_observation_task_ids": [task.observation_task_id for task in group.tasks],
                "grouped_goal_ids": [task.goal_id for task in group.tasks],
                "requested_canonical_keys": group.requested_canonical_keys,
            }
        )
        for record in result.evidence_set.records:
            record.provenance.setdefault("physical_probe_key", list(group.physical_probe_key))
        return result.model_copy(update={"provenance": provenance})

    def _timeout_result(
        self,
        *,
        task: ObservationTask,
        capability: ObservationCapability | None,
        group: PhysicalObservationGroup,
    ) -> ObservationExecutionResult:
        now = self._now()
        error = ObservationExecutionError(
            code="OBSERVER_TIMEOUT",
            message="Post-compile observation probe exceeded the configured timeout.",
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            retryable=True,
            details={
                "timeout_ms": self.budget.max_probe_elapsed_ms,
                "physical_probe_key": list(group.physical_probe_key),
                "late_result_quarantined": True,
            },
        )
        return ObservationExecutionResult(
            observation_task_id=task.observation_task_id,
            goal_id=task.goal_id,
            strategy_id=task.strategy_id,
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            status="BLOCKED_TIMEOUT",
            started_at=now,
            finished_at=now,
            duration_ms=self.budget.max_probe_elapsed_ms,
            evidence_set=EvidenceSet(),
            errors=[error],
            timeline_events=[
                ObservationExecutionTimelineEvent(
                    event_type="observation_execution_blocked",
                    observation_task_id=task.observation_task_id,
                    capability_id=group.capability_id,
                    status="BLOCKED_TIMEOUT",
                    reason_code="OBSERVER_TIMEOUT",
                    message="Late observer result was quarantined after timeout.",
                    timestamp=now,
                    details={"physical_probe_key": list(group.physical_probe_key)},
                )
            ],
            confidence=0.0,
            limitations=["late_result_quarantined_after_timeout"],
            provenance={
                "boundary": "GovernedObservationExecutionStageService",
                "physical_probe_key": list(group.physical_probe_key),
                "grouped_observation_task_ids": [item.observation_task_id for item in group.tasks],
                "grouped_goal_ids": [item.goal_id for item in group.tasks],
                "requested_canonical_keys": group.requested_canonical_keys,
                "late_result_quarantined": True,
            },
        )

    def _runtime_error_result(
        self,
        *,
        task: ObservationTask,
        capability: ObservationCapability | None,
        group: PhysicalObservationGroup,
        exc: Exception,
    ) -> ObservationExecutionResult:
        now = self._now()
        error = ObservationExecutionError(
            code="OBSERVER_RUNTIME_ERROR",
            message=str(exc) or exc.__class__.__name__,
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            retryable=False,
            details={"physical_probe_key": list(group.physical_probe_key)},
        )
        return ObservationExecutionResult(
            observation_task_id=task.observation_task_id,
            goal_id=task.goal_id,
            strategy_id=task.strategy_id,
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            status="BLOCKED_OBSERVER_ERROR",
            started_at=now,
            finished_at=now,
            evidence_set=EvidenceSet(),
            errors=[error],
            provenance={"boundary": "GovernedObservationExecutionStageService", "physical_probe_key": list(group.physical_probe_key)},
        )

    def _fanout_metrics(
        self,
        *,
        groups: list[PhysicalObservationGroup],
        results: list[ObservationExecutionResult],
    ) -> dict[str, Any]:
        evidence_by_group: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
        for result in results:
            key = tuple((result.provenance or {}).get("physical_probe_key") or ())
            if len(key) != 3:
                continue
            rows = evidence_by_group.setdefault((str(key[0]), str(key[1]), str(key[2])), set())
            for record in result.evidence_set.records:
                entity_id = str((record.entity_ref or {}).get("entity_id") or "")
                canonical = str(record.canonical_key or record.attribute_name or "")
                if entity_id and canonical:
                    rows.add((entity_id, canonical))
        satisfied = 0
        unsatisfied = 0
        for group in groups:
            observed = evidence_by_group.get(group.physical_probe_key, set())
            for task in group.tasks:
                canonical = str(task.canonical_key or task.attribute_name or "")
                if (group.entity_id, canonical) in observed:
                    satisfied += 1
                else:
                    unsatisfied += 1
        return {
            "goals_satisfied": satisfied,
            "goals_unsatisfied": unsatisfied,
            "fanout_claim_count": satisfied,
        }

    def _grouping_metrics(self, *, groups: list[PhysicalObservationGroup]) -> dict[str, Any]:
        media_groups = [group for group in groups if group.capability_id == "media_metadata_reader"]
        return {
            "dedup_group_count": len(groups),
            "files_planned": len(media_groups),
            "grouped_observation_task_count": sum(len(group.tasks) for group in groups),
            "requested_canonical_key_count": len({key for group in groups for key in group.requested_canonical_keys}),
        }

    def _group_metrics(self, group: PhysicalObservationGroup) -> dict[str, Any]:
        return {
            "physical_probe_key": list(group.physical_probe_key),
            "entity_id": group.entity_id,
            "capability_id": group.capability_id,
            "grouped_observation_task_count": len(group.tasks),
            "requested_canonical_key_count": len(group.requested_canonical_keys),
        }

    def _is_deferred_executable_task(self, task: ObservationTask) -> bool:
        return bool(
            task.status == "PLANNED"
            and task.execution_disposition == "deferred_by_compile_policy"
            and task.pre_defer_status == "READY_FOR_OBSERVER"
            and task.capability_id
        )

    def _target_entity_ids(self, task: ObservationTask) -> list[str]:
        rows = [
            *[str(item) for item in task.entity_ref.get("entity_ids") or [] if str(item)],
            *[str(item) for item in task.inputs.get("target_entity_ids") or [] if str(item)],
        ]
        if task.entity_ref.get("entity_id"):
            rows.append(str(task.entity_ref.get("entity_id")))
        return list(dict.fromkeys(rows))

    def _normalized_source_ref(self, *, task: ObservationTask, entity: dict[str, Any]) -> str:
        source = (
            task.inputs.get("source_ref")
            or task.inputs.get("file_path")
            or task.inputs.get("raw_ref")
            or self._source_ref_for_entity(entity)
        )
        text = str(source or "").strip().replace("\\", "/")
        return text or f"entity:{entity.get('entity_id')}"

    def _source_ref_for_entity(self, entity: dict[str, Any]) -> str:
        for key in ("path", "absolute_path", "file_path", "source_ref", "raw_ref"):
            value = entity.get(key)
            if value not in (None, ""):
                return str(value)
        attributes = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
        for key in ("path", "absolute_path", "file_path", "source_ref", "relative_path"):
            value = attributes.get(key)
            if isinstance(value, dict):
                value = value.get("value")
            if value not in (None, ""):
                return str(value)
        return ""

    def _execution_entity_ref(self, *, entity: dict[str, Any], capability_id: str) -> dict[str, Any]:
        return {
            "entity_id": str(entity.get("entity_id") or ""),
            "entity_role": str(entity.get("entity_role") or entity.get("role") or ""),
            "entity_kind": str(entity.get("entity_kind") or entity.get("kind") or ""),
            "source_root_role": str(entity.get("source_root_role") or entity.get("root_role") or ""),
            "path": self._source_ref_for_entity(entity),
            "capability_id": capability_id,
        }

    def _checkpoint(self, checkpoint: Callable[[str, dict[str, Any]], None] | None, stage: str, metrics: dict[str, Any]) -> None:
        if checkpoint is None:
            return
        checkpoint(stage, {**metrics, "bounded": True})

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
