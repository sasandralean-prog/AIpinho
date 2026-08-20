from __future__ import annotations

import json
import threading
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
    max_quarantined_workers: int = 1


@dataclass(frozen=True)
class PhysicalObservationGroup:
    physical_probe_key: tuple[str, str, str]
    entity_id: str
    capability_id: str
    normalized_source_ref: str
    raw_execution_source_ref: str
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


_QUARANTINED_PROBES: list[tuple[Future[ObservationExecutionResult], ThreadPoolExecutor, dict[str, Any]]] = []
_QUARANTINE_LOCK = threading.Lock()
_ACTIVE_PROBE_SLOTS = 0


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
        quarantine_block = self._quarantine_block_reason()
        if quarantine_block:
            telemetry = self._blocked_telemetry(reason_code=quarantine_block)
            self._checkpoint(checkpoint, "after_post_compile_observation_execution", telemetry)
            return GovernedObservationExecutionStageResult(
                observation_execution_results=[],
                telemetry=telemetry,
                physical_groups=[],
                blocked_reason_code=quarantine_block,
            )
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
        materialized_observation_bytes = 0
        for index, group in enumerate(groups, start=1):
            if index > self.budget.max_physical_probes:
                blocked_reason = "POST_COMPILE_OBSERVATION_PHYSICAL_PROBE_BUDGET_EXCEEDED"
                break
            if (time.monotonic() - started) * 1000 > self.budget.max_total_observation_elapsed_ms:
                blocked_reason = "POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED"
                break
            quarantine_block = self._quarantine_block_reason()
            if quarantine_block:
                blocked_reason = quarantine_block
                break
            self._checkpoint(
                checkpoint,
                "before_physical_probe",
                {**self._group_metrics(group), "physical_probe_index": index},
            )
            result, probe_blocked_reason = self._execute_group(group=group, checkpoint=checkpoint, stage_started=started)
            if result is None:
                blocked_reason = probe_blocked_reason
                self._checkpoint(
                    checkpoint,
                    "after_physical_probe",
                    {
                        **self._group_metrics(group),
                        "physical_probe_index": index,
                        "physical_probe_status": "BLOCKED_POLICY",
                        "evidence_record_count": 0,
                        "blocked_reason_code": blocked_reason,
                    },
                )
                break
            result_bytes = self._materialized_result_bytes(result)
            if materialized_observation_bytes + result_bytes > self.budget.max_materialized_observation_bytes:
                blocked_reason = "POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED"
                result = self._budget_block_result(
                    group=group,
                    original_result=result,
                    reason_code=blocked_reason,
                    result_bytes=result_bytes,
                    materialized_observation_bytes=materialized_observation_bytes,
                )
                results.append(result)
                self._checkpoint(
                    checkpoint,
                    "after_physical_probe",
                    {
                        **self._group_metrics(group),
                        "physical_probe_index": index,
                        "physical_probe_status": result.status,
                        "evidence_record_count": 0,
                        "materialized_observation_bytes": materialized_observation_bytes,
                        "blocked_reason_code": blocked_reason,
                    },
                )
                break
            record_count = len(getattr(result.evidence_set, "records", []) or [])
            if evidence_records_created + record_count > self.budget.max_evidence_records:
                blocked_reason = "POST_COMPILE_OBSERVATION_EVIDENCE_RECORD_BUDGET_EXCEEDED"
                result = self._evidence_record_budget_block_result(
                    group=group,
                    original_result=result,
                    record_count=record_count,
                    accepted_evidence_records=evidence_records_created,
                )
                record_count = 0
                results.append(result)
                self._checkpoint(
                    checkpoint,
                    "after_physical_probe",
                    {
                        **self._group_metrics(group),
                        "physical_probe_index": index,
                        "physical_probe_status": result.status,
                        "evidence_record_count": 0,
                        "accepted_evidence_records": evidence_records_created,
                        "blocked_reason_code": blocked_reason,
                    },
                )
                break
            materialized_observation_bytes += result_bytes
            results.append(result)
            evidence_records_created += record_count
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
            if probe_blocked_reason:
                blocked_reason = probe_blocked_reason
                break
            if consecutive_failures > 0 and consecutive_failures >= self.budget.max_consecutive_execution_failures:
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
            "materialized_observation_bytes": materialized_observation_bytes,
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
            if not capability_id or not self._capability_available(capability_id):
                continue
            for entity_id in self._target_entity_ids(task):
                entity = entities_by_id.get(entity_id)
                if entity is None:
                    continue
                raw_source_ref = self._raw_source_ref(task=task, entity=entity)
                source_ref = self._normalized_source_ref(raw_source_ref=raw_source_ref, entity=entity)
                key = (entity_id, capability_id, source_ref)
                group = groups.get(key)
                if group is None:
                    group = PhysicalObservationGroup(
                        physical_probe_key=key,
                        entity_id=entity_id,
                        capability_id=capability_id,
                        normalized_source_ref=source_ref,
                        raw_execution_source_ref=raw_source_ref,
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
    ) -> tuple[ObservationExecutionResult | None, str | None]:
        task = self._execution_task_for_group(group)
        capability = self.observer_registry.get(group.capability_id)
        if not self._capability_available(group.capability_id):
            return self._capability_unavailable_result(task=task, capability=capability, group=group), "POST_COMPILE_OBSERVATION_CAPABILITY_UNAVAILABLE"
        if not self._try_acquire_probe_slot():
            return None, "POST_COMPILE_OBSERVATION_WORKER_BOUND_OCCUPIED"
        policy = ObservationExecutionPolicy(timeout_ms=self.budget.max_probe_elapsed_ms)
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aipinho_observer_probe")
        future: Future[ObservationExecutionResult] = executor.submit(
            self.observation_boundary.execute,
            task=task,
            capability=capability,
            policy=policy,
        )
        probe_deadline = time.monotonic() + (self.budget.max_probe_elapsed_ms / 1000)
        stage_deadline = stage_started + (self.budget.max_total_observation_elapsed_ms / 1000)
        try:
            while True:
                now = time.monotonic()
                remaining_probe = probe_deadline - now
                remaining_stage = stage_deadline - now
                if remaining_probe <= 0 or remaining_stage <= 0:
                    break
                wait_seconds = min(
                    max(0.001, remaining_probe),
                    max(0.001, remaining_stage),
                    max(0.001, self.budget.heartbeat_interval_ms / 1000),
                )
                try:
                    result = future.result(timeout=wait_seconds)
                    executor.shutdown(wait=False, cancel_futures=True)
                    self._release_probe_slot()
                    return self._with_physical_provenance(result, group=group), None
                except TimeoutError:
                    self._checkpoint(
                        checkpoint,
                        "physical_probe_checkpoint",
                        {
                            **self._group_metrics(group),
                            "elapsed_ms": round((time.monotonic() - stage_started) * 1000, 3),
                            "probe_elapsed_ms": round((self.budget.max_probe_elapsed_ms / 1000 - max(0.0, remaining_probe)) * 1000, 3),
                        },
                    )
            remaining_stage = stage_deadline - time.monotonic()
            reason_code = (
                "POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED"
                if remaining_stage <= 0
                else "POST_COMPILE_PHYSICAL_PROBE_TIMEOUT"
            )
            self._register_quarantined_probe(future=future, executor=executor, group=group, reason_code=reason_code)
            timeout_result = self._timeout_result(task=task, capability=capability, group=group, reason_code=reason_code)
            return timeout_result, reason_code
        except Exception as exc:
            executor.shutdown(wait=False, cancel_futures=True)
            self._release_probe_slot()
            return self._runtime_error_result(task=task, capability=capability, group=group, exc=exc), None

    def _execution_task_for_group(self, group: PhysicalObservationGroup) -> ObservationTask:
        first = group.tasks[0]
        entity_ref = self._execution_entity_ref(entity=group.entity, capability_id=group.capability_id)
        expected_outputs = sorted(MEDIA_METADATA_EVIDENCE_KEYS) if group.capability_id == "media_metadata_reader" else group.requested_canonical_keys
        return first.model_copy(
            update={
                "status": "READY_FOR_OBSERVER",
                "entity_ref": entity_ref,
                "inputs": {
                    **dict(first.inputs or {}),
                    "entity_id": group.entity_id,
                    "file_path": group.raw_execution_source_ref,
                    "source_ref": group.raw_execution_source_ref,
                    "normalized_source_ref": group.normalized_source_ref,
                    "entity_role": entity_ref.get("entity_role"),
                    "source_root_role": entity_ref.get("source_root_role"),
                    "required_confidence": first.inputs.get("required_confidence", 0.0),
                },
                "expected_outputs": expected_outputs,
                "created_from": {
                    **dict(first.created_from or {}),
                    "physical_probe_key": list(group.physical_probe_key),
                    "raw_execution_source_ref": group.raw_execution_source_ref,
                    "normalized_source_ref": group.normalized_source_ref,
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
                "raw_execution_source_ref": group.raw_execution_source_ref,
                "normalized_source_ref": group.normalized_source_ref,
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
        reason_code: str,
    ) -> ObservationExecutionResult:
        now = self._now()
        error = ObservationExecutionError(
            code="OBSERVER_TIMEOUT",
            message="Post-compile observation probe exceeded a governed execution deadline.",
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            retryable=True,
            details={
                "timeout_ms": self.budget.max_probe_elapsed_ms,
                "total_budget_ms": self.budget.max_total_observation_elapsed_ms,
                "physical_probe_key": list(group.physical_probe_key),
                "late_result_quarantined": True,
                "blocked_reason_code": reason_code,
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
                    reason_code=reason_code,
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
                "raw_execution_source_ref": group.raw_execution_source_ref,
                "grouped_observation_task_ids": [item.observation_task_id for item in group.tasks],
                "grouped_goal_ids": [item.goal_id for item in group.tasks],
                "requested_canonical_keys": group.requested_canonical_keys,
                "late_result_quarantined": True,
                "blocked_reason_code": reason_code,
            },
        )

    def _budget_block_result(
        self,
        *,
        group: PhysicalObservationGroup,
        original_result: ObservationExecutionResult,
        reason_code: str,
        result_bytes: int,
        materialized_observation_bytes: int,
    ) -> ObservationExecutionResult:
        now = self._now()
        capability = self.observer_registry.get(group.capability_id)
        error = ObservationExecutionError(
            code="OBSERVER_POLICY_BLOCKED",
            message="Post-compile observation evidence exceeded the materialized observation budget.",
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            retryable=False,
            details={
                "blocked_reason_code": reason_code,
                "result_bytes": result_bytes,
                "materialized_observation_bytes": materialized_observation_bytes,
                "max_materialized_observation_bytes": self.budget.max_materialized_observation_bytes,
                "physical_probe_key": list(group.physical_probe_key),
            },
        )
        return ObservationExecutionResult(
            observation_task_id=original_result.observation_task_id,
            goal_id=original_result.goal_id,
            strategy_id=original_result.strategy_id,
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            status="BLOCKED_POLICY",
            started_at=original_result.started_at,
            finished_at=now,
            duration_ms=original_result.duration_ms,
            evidence_set=EvidenceSet(),
            errors=[error],
            confidence=0.0,
            limitations=["materialized_observation_bytes_budget_exceeded"],
            provenance={
                "boundary": "GovernedObservationExecutionStageService",
                "physical_probe_key": list(group.physical_probe_key),
                "raw_execution_source_ref": group.raw_execution_source_ref,
                "grouped_observation_task_ids": [item.observation_task_id for item in group.tasks],
                "grouped_goal_ids": [item.goal_id for item in group.tasks],
                "requested_canonical_keys": group.requested_canonical_keys,
                "blocked_reason_code": reason_code,
            },
        )

    def _evidence_record_budget_block_result(
        self,
        *,
        group: PhysicalObservationGroup,
        original_result: ObservationExecutionResult,
        record_count: int,
        accepted_evidence_records: int,
    ) -> ObservationExecutionResult:
        now = self._now()
        capability = self.observer_registry.get(group.capability_id)
        reason_code = "POST_COMPILE_OBSERVATION_EVIDENCE_RECORD_BUDGET_EXCEEDED"
        error = ObservationExecutionError(
            code="OBSERVER_POLICY_BLOCKED",
            message="Post-compile observation evidence exceeded the evidence-record budget.",
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            retryable=False,
            details={
                "blocked_reason_code": reason_code,
                "result_evidence_record_count": record_count,
                "accepted_evidence_records": accepted_evidence_records,
                "max_evidence_records": self.budget.max_evidence_records,
                "physical_probe_key": list(group.physical_probe_key),
            },
        )
        return ObservationExecutionResult(
            observation_task_id=original_result.observation_task_id,
            goal_id=original_result.goal_id,
            strategy_id=original_result.strategy_id,
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            status="BLOCKED_POLICY",
            started_at=original_result.started_at,
            finished_at=now,
            duration_ms=original_result.duration_ms,
            evidence_set=EvidenceSet(),
            errors=[error],
            confidence=0.0,
            limitations=["evidence_record_budget_exceeded"],
            provenance={
                "boundary": "GovernedObservationExecutionStageService",
                "physical_probe_key": list(group.physical_probe_key),
                "raw_execution_source_ref": group.raw_execution_source_ref,
                "grouped_observation_task_ids": [item.observation_task_id for item in group.tasks],
                "grouped_goal_ids": [item.goal_id for item in group.tasks],
                "requested_canonical_keys": group.requested_canonical_keys,
                "blocked_reason_code": reason_code,
            },
        )

    def _capability_unavailable_result(
        self,
        *,
        task: ObservationTask,
        capability: ObservationCapability | None,
        group: PhysicalObservationGroup,
    ) -> ObservationExecutionResult:
        now = self._now()
        error = ObservationExecutionError(
            code="OBSERVER_POLICY_BLOCKED",
            message="Post-compile observation capability was unavailable before physical execution.",
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            retryable=False,
            details={"physical_probe_key": list(group.physical_probe_key), "blocked_reason_code": "POST_COMPILE_OBSERVATION_CAPABILITY_UNAVAILABLE"},
        )
        return ObservationExecutionResult(
            observation_task_id=task.observation_task_id,
            goal_id=task.goal_id,
            strategy_id=task.strategy_id,
            capability_id=group.capability_id,
            observer_id=(capability.observer_binding or {}).get("observer_id") if capability else None,
            status="BLOCKED_POLICY",
            started_at=now,
            finished_at=now,
            evidence_set=EvidenceSet(),
            errors=[error],
            provenance={"boundary": "GovernedObservationExecutionStageService", "physical_probe_key": list(group.physical_probe_key)},
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
            "raw_execution_source_ref_present": bool(group.raw_execution_source_ref),
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

    def _raw_source_ref(self, *, task: ObservationTask, entity: dict[str, Any]) -> str:
        source = (
            task.inputs.get("file_path")
            or task.inputs.get("source_ref")
            or task.inputs.get("raw_ref")
            or self._source_ref_for_entity(entity)
        )
        return str(source or "").strip() or f"entity:{entity.get('entity_id')}"

    def _normalized_source_ref(self, *, raw_source_ref: str, entity: dict[str, Any]) -> str:
        text = str(raw_source_ref or "").strip().replace("\\", "/")
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
        source_root = str(entity.get("source_root") or self._attribute_value(entity, "source_root") or "").strip()
        relative_path = str(entity.get("relative_path") or self._attribute_value(entity, "relative_path") or "").strip()
        if source_root and relative_path:
            root = source_root.rstrip("/\\")
            relative = relative_path.lstrip("/\\")
            return f"{root}\\{relative}"
        return ""

    def _execution_entity_ref(self, *, entity: dict[str, Any], capability_id: str) -> dict[str, Any]:
        source_root_role = str(entity.get("source_root_role") or entity.get("root_role") or self._attribute_value(entity, "source_root_role") or "")
        entity_role = str(entity.get("entity_role") or entity.get("role") or self._attribute_value(entity, "entity_role") or "")
        if capability_id == "media_metadata_reader" and source_root_role in {"library_root", "corpus_root"} and entity_role != "media_asset_candidate":
            execution_role = "media_asset_candidate"
        else:
            execution_role = entity_role
        return {
            "entity_id": str(entity.get("entity_id") or ""),
            "entity_role": execution_role,
            "original_entity_role": entity_role,
            "entity_kind": str(entity.get("entity_kind") or entity.get("kind") or ""),
            "source_root_role": source_root_role,
            "source_root": str(entity.get("source_root") or self._attribute_value(entity, "source_root") or ""),
            "relative_path": str(entity.get("relative_path") or self._attribute_value(entity, "relative_path") or ""),
            "path": self._source_ref_for_entity(entity),
            "capability_id": capability_id,
            "observation_hypothesis": "media_asset_candidate_for_contract_required_metadata" if execution_role != entity_role else None,
        }

    def _attribute_value(self, entity: dict[str, Any], key: str) -> Any:
        attributes = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
        value = attributes.get(key)
        if value is None:
            observed_attributes = entity.get("observed_attributes") if isinstance(entity.get("observed_attributes"), dict) else {}
            value = observed_attributes.get(key)
        if isinstance(value, dict):
            return value.get("value")
        return value

    def _checkpoint(self, checkpoint: Callable[[str, dict[str, Any]], None] | None, stage: str, metrics: dict[str, Any]) -> None:
        if checkpoint is None:
            return
        checkpoint(stage, {**metrics, "bounded": True})

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _capability_available(self, capability_id: str) -> bool:
        capability = self.observer_registry.get(capability_id)
        return bool(capability is not None and capability.available and str(capability.status or "available") not in {"disabled", "unavailable", "blocked"})

    def _materialized_result_bytes(self, result: ObservationExecutionResult) -> int:
        try:
            payload = result.evidence_set.model_dump(mode="json")
        except Exception:
            payload = {"records": []}
        return len(json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8"))

    def _blocked_telemetry(self, *, reason_code: str) -> dict[str, Any]:
        return {
            "dedup_group_count": 0,
            "files_planned": 0,
            "grouped_observation_task_count": 0,
            "requested_canonical_key_count": 0,
            "goals_satisfied": 0,
            "goals_unsatisfied": 0,
            "fanout_claim_count": 0,
            "physical_probe_count": 0,
            "files_attempted": 0,
            "files_succeeded": 0,
            "files_failed": 0,
            "evidence_records_created": 0,
            "materialized_observation_bytes": 0,
            "execution_status": "blocked",
            "blocked_reason_code": reason_code,
        }

    def _register_quarantined_probe(
        self,
        *,
        future: Future[ObservationExecutionResult],
        executor: ThreadPoolExecutor,
        group: PhysicalObservationGroup,
        reason_code: str,
    ) -> None:
        global _ACTIVE_PROBE_SLOTS
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        with _QUARANTINE_LOCK:
            _ACTIVE_PROBE_SLOTS = max(0, _ACTIVE_PROBE_SLOTS - 1)
            _QUARANTINED_PROBES.append(
                (
                    future,
                    executor,
                    {
                        "physical_probe_key": list(group.physical_probe_key),
                        "reason_code": reason_code,
                        "registered_at_monotonic": time.monotonic(),
                    },
                )
            )

    def _quarantine_block_reason(self) -> str | None:
        self._reap_quarantined_workers()
        with _QUARANTINE_LOCK:
            occupied = _ACTIVE_PROBE_SLOTS + len(_QUARANTINED_PROBES)
        if occupied >= self.budget.max_quarantined_workers and len(_QUARANTINED_PROBES) > 0:
            return "POST_COMPILE_OBSERVATION_QUARANTINE_BOUND_OCCUPIED"
        return None

    def _reap_quarantined_workers(self) -> None:
        with _QUARANTINE_LOCK:
            pending: list[tuple[Future[ObservationExecutionResult], ThreadPoolExecutor, dict[str, Any]]] = []
            for future, executor, metadata in _QUARANTINED_PROBES:
                if future.done() or future.cancelled():
                    executor.shutdown(wait=False, cancel_futures=True)
                    continue
                pending.append((future, executor, metadata))
            _QUARANTINED_PROBES[:] = pending

    def _try_acquire_probe_slot(self) -> bool:
        global _ACTIVE_PROBE_SLOTS
        self._reap_quarantined_workers()
        with _QUARANTINE_LOCK:
            occupied = _ACTIVE_PROBE_SLOTS + len(_QUARANTINED_PROBES)
            if occupied >= self.budget.max_quarantined_workers:
                return False
            _ACTIVE_PROBE_SLOTS += 1
            return True

    def _release_probe_slot(self) -> None:
        global _ACTIVE_PROBE_SLOTS
        with _QUARANTINE_LOCK:
            _ACTIVE_PROBE_SLOTS = max(0, _ACTIVE_PROBE_SLOTS - 1)
