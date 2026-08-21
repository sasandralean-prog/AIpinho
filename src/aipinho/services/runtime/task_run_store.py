from __future__ import annotations
import json
import re
import hashlib
import time
from threading import RLock
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.runtime.task_run_trace import TaskRunTraceItem
from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
from aipinho.services.runtime.phase_semantic_result_finalizer import PhaseSemanticResultFinalizer
from aipinho.services.runtime.runtime_payload_ref_store import RuntimePayloadRefStore
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file

_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+")
_SENSITIVE_KEYS = {"content", "raw", "raw_content", "full_prompt", "prompt", "full_model_output", "model_output", "password", "secret", "token", "api_key"}
_HEAVY_RUNTIME_KEYS = {
    "artifacts",
    "artifact_semantic_profiles",
    "artifact_semantic_validations",
    "attribute_observations",
    "candidate_entity_set",
    "contract_observation_plan",
    "entities",
    "evidence_set",
    "knowledge_records",
    "metadata",
    "observation_execution_results",
    "observation_plan",
    "perception",
    "produced_artifacts",
    "provenance",
    "semantic_assertions",
    "semantic_self_review",
    "specialization_hypotheses",
}
_MEDIA_INVENTORY_STAGE_STALL_REASONS: dict[str, str] = {
    "after_entity_selection": "MUSIC_INVENTORY_PERCEPTION_PAYLOAD_COMPILE_STALLED",
    "before_perception_payload_compile": "MUSIC_INVENTORY_PERCEPTION_PAYLOAD_COMPILE_STALLED",
    "before_compile_request_normalization": "PERCEPTION_PAYLOAD_COMPILE_BUDGET_EXCEEDED",
    "after_compile_request_normalization": "PERCEPTION_REQUIREMENT_RESOLUTION_STALLED",
    "before_requirement_resolution": "PERCEPTION_REQUIREMENT_RESOLUTION_STALLED",
    "after_requirement_resolution": "PERCEPTION_ENTITY_PROJECTION_STALLED",
    "before_entity_projection": "PERCEPTION_ENTITY_PROJECTION_STALLED",
    "entity_projection_checkpoint": "PERCEPTION_ENTITY_PROJECTION_STALLED",
    "after_entity_projection": "PERCEPTION_RELATIONSHIP_PROJECTION_STALLED",
    "before_relationship_projection": "PERCEPTION_RELATIONSHIP_PROJECTION_STALLED",
    "after_relationship_projection": "PERCEPTION_OBSERVATION_BINDING_STALLED",
    "before_observation_binding": "PERCEPTION_OBSERVATION_BINDING_STALLED",
    "before_observation_goal_projection": "PERCEPTION_OBSERVATION_GOAL_PROJECTION_STALLED",
    "after_observation_goal_projection": "PERCEPTION_OBSERVATION_STRATEGY_PROJECTION_STALLED",
    "before_observation_strategy_projection": "PERCEPTION_OBSERVATION_STRATEGY_PROJECTION_STALLED",
    "after_observation_strategy_projection": "PERCEPTION_CAPABILITY_MATCH_PROJECTION_STALLED",
    "before_capability_match_projection": "PERCEPTION_CAPABILITY_MATCH_PROJECTION_STALLED",
    "after_capability_match_projection": "PERCEPTION_CAPABILITY_DECISION_PROJECTION_STALLED",
    "before_capability_decision_projection": "PERCEPTION_CAPABILITY_DECISION_PROJECTION_STALLED",
    "after_capability_decision_projection": "PERCEPTION_OBSERVATION_TASK_PROJECTION_STALLED",
    "before_observation_task_projection": "PERCEPTION_OBSERVATION_TASK_PROJECTION_STALLED",
    "after_observation_task_projection": "PERCEPTION_OBSERVATION_REQUIREMENT_PROJECTION_STALLED",
    "before_observation_requirement_projection": "PERCEPTION_OBSERVATION_REQUIREMENT_PROJECTION_STALLED",
    "after_observation_requirement_projection": "PERCEPTION_OBSERVATION_BINDING_STALLED",
    "after_observation_binding": "PERCEPTION_FACT_PROJECTION_STALLED",
    "before_fact_projection": "PERCEPTION_FACT_PROJECTION_STALLED",
    "before_fact_source_binding": "PERCEPTION_FACT_SOURCE_BINDING_STALLED",
    "before_source_index_build": "PERCEPTION_FACT_SOURCE_BINDING_STALLED",
    "after_source_index_build": "PERCEPTION_ATTRIBUTE_OBSERVATION_PROJECTION_STALLED",
    "before_attribute_observation_projection": "PERCEPTION_ATTRIBUTE_OBSERVATION_PROJECTION_STALLED",
    "attribute_observation_projection_checkpoint": "PERCEPTION_ATTRIBUTE_OBSERVATION_PROJECTION_STALLED",
    "after_attribute_observation_projection": "PERCEPTION_EVIDENCE_REF_RESOLUTION_STALLED",
    "before_evidence_ref_resolution": "PERCEPTION_EVIDENCE_REF_RESOLUTION_STALLED",
    "after_evidence_ref_resolution": "PERCEPTION_EVIDENCE_SET_MATERIALIZATION_STALLED",
    "before_evidence_set_materialization": "PERCEPTION_EVIDENCE_SET_MATERIALIZATION_STALLED",
    "evidence_set_materialization_checkpoint": "PERCEPTION_EVIDENCE_SET_MATERIALIZATION_STALLED",
    "after_evidence_set_materialization": "PERCEPTION_SOURCE_PROVENANCE_BINDING_STALLED",
    "before_source_provenance_binding": "PERCEPTION_SOURCE_PROVENANCE_BINDING_STALLED",
    "after_source_provenance_binding": "PERCEPTION_SOURCE_BINDING_BOUND_CHECK_STALLED",
    "before_source_binding_bound_check": "PERCEPTION_SOURCE_BINDING_BOUND_CHECK_STALLED",
    "after_source_binding_bound_check": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
    "fact_source_binding_completed": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
    "after_fact_source_binding": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
    "before_fact_candidate_projection": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
    "after_fact_candidate_projection": "PERCEPTION_FACT_DERIVATION_STALLED",
    "before_fact_derivation": "PERCEPTION_FACT_DERIVATION_STALLED",
    "fact_derivation_checkpoint": "PERCEPTION_FACT_DERIVATION_STALLED",
    "after_fact_derivation": "PERCEPTION_FACT_PROVENANCE_BINDING_STALLED",
    "before_fact_provenance_binding": "PERCEPTION_FACT_PROVENANCE_BINDING_STALLED",
    "after_fact_provenance_binding": "PERCEPTION_FACT_DEDUPLICATION_STALLED",
    "before_fact_deduplication": "PERCEPTION_FACT_DEDUPLICATION_STALLED",
    "after_fact_deduplication": "PERCEPTION_FACT_VALIDATION_PROJECTION_STALLED",
    "before_fact_validation_projection": "PERCEPTION_FACT_VALIDATION_PROJECTION_STALLED",
    "after_fact_validation_projection": "PERCEPTION_PAYLOAD_ASSEMBLY_STALLED",
    "fact_projection_completed": "PERCEPTION_PAYLOAD_ASSEMBLY_STALLED",
    "after_fact_projection": "PERCEPTION_PAYLOAD_ASSEMBLY_STALLED",
    "before_payload_assembly": "PERCEPTION_PAYLOAD_ASSEMBLY_STALLED",
    "after_payload_assembly": "PERCEPTION_PAYLOAD_BOUND_EXCEEDED",
    "before_payload_bound_check": "PERCEPTION_PAYLOAD_BOUND_EXCEEDED",
    "after_payload_bound_check": "PERCEPTION_PAYLOAD_COMPILE_BUDGET_EXCEEDED",
    "perception_compile_completed": "MUSIC_INVENTORY_CONTRACT_PERCEPTION_STALLED",
    "after_perception_payload_compile": "MUSIC_INVENTORY_CONTRACT_PERCEPTION_STALLED",
    "before_post_compile_observation_execution": "POST_COMPILE_OBSERVATION_GROUP_PLANNING_STALLED",
    "before_observation_physical_group_planning": "POST_COMPILE_OBSERVATION_GROUP_PLANNING_STALLED",
    "observation_task_scan_checkpoint": "POST_COMPILE_OBSERVATION_TASK_SCAN_STALLED",
    "after_observation_task_scan": "POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED",
    "before_capability_applicability_resolution": "POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED",
    "capability_applicability_resolution_checkpoint": "POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED",
    "after_capability_applicability_resolution": "POST_COMPILE_BACKEND_AVAILABILITY_SNAPSHOT_STALLED",
    "after_observation_physical_group_planning": "POST_COMPILE_BACKEND_AVAILABILITY_SNAPSHOT_STALLED",
    "before_backend_availability_snapshot": "POST_COMPILE_BACKEND_AVAILABILITY_SNAPSHOT_STALLED",
    "after_backend_availability_snapshot": "POST_COMPILE_PHYSICAL_PROBE_DISPATCH_STALLED",
    "after_observation_task_grouping": "POST_COMPILE_PHYSICAL_PROBE_DISPATCH_STALLED",
    "before_physical_probe_dispatch": "POST_COMPILE_PHYSICAL_PROBE_DISPATCH_STALLED",
    "before_physical_probe": "POST_COMPILE_PHYSICAL_PROBE_STALLED",
    "physical_probe_checkpoint": "POST_COMPILE_PHYSICAL_PROBE_STALLED",
    "after_physical_probe": "POST_COMPILE_EVIDENCE_FANOUT_STALLED",
    "after_evidence_fanout": "POST_COMPILE_EVIDENCE_FANOUT_STALLED",
    "after_post_compile_observation_execution": "POST_COMPILE_OBSERVATION_EXECUTION_STALLED",
    "before_post_execution_perception_materialization": "POST_EXECUTION_PERCEPTION_MATERIALIZATION_STALLED",
    "after_post_execution_evidence_application": "POST_EXECUTION_PERCEPTION_MATERIALIZATION_STALLED",
    "after_post_execution_attribute_observation_materialization": "POST_EXECUTION_PERCEPTION_MATERIALIZATION_STALLED",
    "after_post_execution_evidence_set_materialization": "POST_EXECUTION_PERCEPTION_MATERIALIZATION_STALLED",
    "after_post_execution_perception_materialization": "MUSIC_INVENTORY_CONTRACT_PERCEPTION_STALLED",
    "before_contract_perception": "MUSIC_INVENTORY_CONTRACT_PERCEPTION_STALLED",
    "after_contract_perception": "MUSIC_INVENTORY_ROW_BINDING_STALLED",
    "before_row_binding": "MUSIC_INVENTORY_ROW_BINDING_STALLED",
    "after_row_binding": "MUSIC_INVENTORY_METADATA_COVERAGE_CALCULATION_STALLED",
    "before_metadata_coverage_summary": "MUSIC_INVENTORY_METADATA_COVERAGE_CALCULATION_STALLED",
    "after_metadata_coverage_summary": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "before_csv_row_stream": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "csv_row_stream_checkpoint": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "before_csv_cell_render": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "after_entity_batch": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "after_csv_row_stream": "MUSIC_INVENTORY_SEMANTIC_PROFILE_BUILD_STALLED",
    "before_artifact_semantic_profile": "MUSIC_INVENTORY_SEMANTIC_PROFILE_BUILD_STALLED",
    "after_artifact_semantic_profile": "MUSIC_INVENTORY_SUFFICIENCY_EVALUATION_STALLED",
    "before_inventory_sufficiency": "MUSIC_INVENTORY_SUFFICIENCY_EVALUATION_STALLED",
    "after_inventory_sufficiency": "MUSIC_INVENTORY_ARTIFACT_PERSIST_STALLED",
    "before_artifact_persist": "MUSIC_INVENTORY_ARTIFACT_PERSIST_STALLED",
    "before_persist_payload_classification": "ARTIFACT_PERSIST_PAYLOAD_CLASSIFICATION_STALLED",
    "after_persist_payload_classification": "ARTIFACT_PERSIST_PAYLOAD_SERIALIZATION_STALLED",
    "before_payload_materialization": "ARTIFACT_PERSIST_PAYLOAD_MATERIALIZATION_STALLED",
    "after_payload_materialization": "ARTIFACT_PERSIST_PAYLOAD_SERIALIZATION_STALLED",
    "before_payload_serialization": "ARTIFACT_PERSIST_PAYLOAD_SERIALIZATION_STALLED",
    "payload_serialization_checkpoint": "ARTIFACT_PERSIST_PAYLOAD_SERIALIZATION_STALLED",
    "after_payload_serialization": "ARTIFACT_PERSIST_PAYLOAD_REF_DECISION_STALLED",
    "before_payload_ref_decision": "ARTIFACT_PERSIST_PAYLOAD_REF_DECISION_STALLED",
    "after_payload_ref_decision": "ARTIFACT_PERSIST_PAYLOAD_REF_PERSIST_STALLED",
    "before_payload_ref_persist": "ARTIFACT_PERSIST_PAYLOAD_REF_PERSIST_STALLED",
    "after_payload_ref_persist": "ARTIFACT_PERSIST_ARTIFACT_CONTENT_WRITE_STALLED",
    "before_artifact_content_write": "ARTIFACT_PERSIST_ARTIFACT_CONTENT_WRITE_STALLED",
    "artifact_content_write_checkpoint": "ARTIFACT_PERSIST_ARTIFACT_CONTENT_WRITE_STALLED",
    "after_artifact_content_write": "ARTIFACT_PERSIST_MANIFEST_BUILD_STALLED",
    "before_manifest_build": "ARTIFACT_PERSIST_MANIFEST_BUILD_STALLED",
    "after_manifest_build": "ARTIFACT_PERSIST_MANIFEST_WRITE_STALLED",
    "before_manifest_persist": "ARTIFACT_PERSIST_MANIFEST_WRITE_STALLED",
    "before_sharded_manifest_persist": "ARTIFACT_PERSIST_MANIFEST_WRITE_STALLED",
    "after_sharded_manifest_persist": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "after_manifest_persist": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "before_registry_index_update": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "before_light_index_persist": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "after_light_index_persist": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "before_legacy_registry_projection": "ARTIFACT_PERSIST_LEGACY_REGISTRY_PROJECTION_STALLED",
    "after_legacy_registry_projection": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "legacy_registry_projection_skipped": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "after_registry_index_update": "ARTIFACT_PERSIST_COMMIT_STALLED",
    "before_artifact_commit": "ARTIFACT_PERSIST_COMMIT_STALLED",
    "after_artifact_commit": "ARTIFACT_PERSIST_COMPLETED",
    "artifact_persist_completed": "ARTIFACT_PERSIST_COMPLETED",
    "after_artifact_persist": "ARTIFACT_PERSIST_COMPLETED",
}

class TaskRunStore:
    _terminal_event_lock = RLock()
    _write_lock = RLock()

    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "runtime" / "task_run_store_policy.yaml", critical=True, root=PATHS.config_root / "runtime")
        configured = str(self.policy.get("store", {}).get("path", "data/runtime/task_runs"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)
        self.payload_refs = RuntimePayloadRefStore(root=self.root)

    def create_run(self, run: TaskRun) -> TaskRun:
        if self.get_run(run.run_id) is not None:
            raise ValueError("task_run_already_exists")
        return self.update_run(run)

    def update_run(self, run: TaskRun) -> TaskRun:
        self._write(self._run_dir(run.run_id) / "run.json", run.model_dump())
        self._write_run_index(run)
        return run

    def get_run(self, run_id: str) -> TaskRun | None:
        data = self._read_task_run(run_id)
        return TaskRun.model_validate(data) if data else None

    def get_run_lightweight(self, run_id: str) -> TaskRun | None:
        """Return a TaskRun projection without hydrating spilled payload refs.

        Public summary/endpoint projections should not parse hundreds of MB of
        preserved runtime evidence just to decide lifecycle state. Spilled refs
        remain available on disk and through full `get_run()` when a caller
        explicitly needs raw diagnostic payloads.
        """
        run_dir = self._run_dir(run_id)
        data = self._read(run_dir / "run.json")
        if not isinstance(data, dict):
            return None
        projected = self._project_payload_refs_for_model(data)
        return TaskRun.model_validate(projected)

    def get_run_index(self, run_id: str) -> dict[str, Any] | None:
        data = self._read(self._run_dir(run_id) / "run_index.json")
        return data if isinstance(data, dict) else None

    def get_run_by_task_id(self, task_id: str) -> TaskRun | None:
        if not task_id or not self.root.exists():
            return None
        for path in self.root.glob("*/run.json"):
            try:
                run = self.get_run(path.parent.name)
            except Exception:
                continue
            if run is None:
                continue
            if run.task_id == task_id or run.run_id == task_id or run.task_run_id == task_id:
                return run
        return None

    def list_runs(self, *, status: str | None = None, session_id: str | None = None, draft_id: str | None = None, contract_type: str | None = None, created_after: str | None = None, limit: int = 100) -> list[TaskRun]:
        if not self.root.exists():
            return []
        runs: list[TaskRun] = []
        for path in self.root.glob("*/run.json"):
            try:
                run = self.get_run(path.parent.name)
            except Exception:
                continue
            if run is None:
                continue
            if status and run.status != status: continue
            if session_id and run.session_id != session_id: continue
            if draft_id and run.draft_id != draft_id: continue
            if contract_type and run.contract_type != contract_type: continue
            if created_after and run.created_at < created_after: continue
            runs.append(run)
        return sorted(runs, key=lambda item: item.created_at, reverse=True)[: max(1, min(limit, 1000))]

    def list_queue_runs(self, *, active_statuses: set[str], limit: int = 1000) -> list[TaskRun]:
        """Return runs relevant to queue reconciliation without parsing terminal history."""
        if not self.root.exists():
            return []
        runs: list[TaskRun] = []
        for run_dir in self.root.glob("task_run_*"):
            if not run_dir.is_dir():
                continue
            index = self._read(run_dir / "run_index.json")
            if isinstance(index, dict):
                status = str(index.get("status") or "")
                if status not in active_statuses:
                    continue
                run = self.get_run_lightweight(str(index.get("run_id") or run_dir.name))
                if run is not None:
                    runs.append(run)
                continue
            if (run_dir / "result.json").exists():
                continue
            run = self.get_run_lightweight(run_dir.name)
            if run is not None and run.status in active_statuses:
                self._write_run_index(run)
                runs.append(run)
        return sorted(runs, key=lambda item: item.created_at, reverse=True)[: max(1, min(limit, 1000))]

    def compact_run_storage(self, run_id: str) -> dict[str, Any]:
        """Rewrite a TaskRun through the governed lightweight storage path.

        This preserves the canonical JSON documents while spilling heavy runtime
        payloads into payload_refs and rebuilding the queue projection index.
        """
        run_dir = self._run_dir(run_id)
        run_path = run_dir / "run.json"
        before_bytes = run_path.stat().st_size if run_path.exists() else 0
        data = self._read(run_path)
        if not isinstance(data, dict):
            return {
                "run_id": run_id,
                "status": "missing_or_invalid",
                "before_bytes": before_bytes,
                "after_bytes": before_bytes,
                "valid_json": False,
                "index_written": False,
                "payload_ref_count": len(list((run_dir / "payload_refs").glob("*.json"))) if (run_dir / "payload_refs").exists() else 0,
            }
        self._write(run_path, data)
        self._write_run_index_from_data(run_id, self._read(run_path) or data)
        after_bytes = run_path.stat().st_size if run_path.exists() else 0
        valid_json = isinstance(self._read(run_path), dict)
        return {
            "run_id": run_id,
            "status": "compacted" if after_bytes <= before_bytes else "rewritten",
            "before_bytes": before_bytes,
            "after_bytes": after_bytes,
            "saved_bytes": max(0, before_bytes - after_bytes),
            "valid_json": valid_json,
            "index_written": (run_dir / "run_index.json").exists(),
            "payload_ref_count": len(list((run_dir / "payload_refs").glob("*.json"))) if (run_dir / "payload_refs").exists() else 0,
            "result_preserved": (run_dir / "result.json").exists(),
            "events_preserved": (run_dir / "events.json").exists(),
        }

    def rebuild_run_index(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        data = self._read(run_dir / "run.json")
        if not isinstance(data, dict):
            return {"run_id": run_id, "status": "missing_or_invalid", "index_written": False}
        self._write_run_index_from_data(run_id, data)
        return {"run_id": run_id, "status": "indexed", "index_written": (run_dir / "run_index.json").exists()}

    def append_event(self, run_id: str, event: TaskRunEvent) -> TaskRunEvent:
        with self._terminal_event_lock:
            if event.type in self._terminal_event_types():
                terminal = self._first_terminal_event(run_id)
                if terminal is not None:
                    reason_code = str((event.metadata or {}).get("reason_code") or event.type)
                    self._append_terminalization_ignored(
                        run_id,
                        attempted_status=event.status,
                        reason_code=reason_code,
                        terminal_event=terminal,
                    )
                    ignored = [
                        item
                        for item in self.get_events(run_id)
                        if item.type == "terminalization_already_applied"
                        and (item.metadata or {}).get("terminal_event_id") == terminal.event_id
                        and (item.metadata or {}).get("attempted_reason_code") == reason_code
                    ]
                    return ignored[-1] if ignored else terminal
            events = self.get_events(run_id)
            events.append(event)
            self._write(self._run_dir(run_id) / "events.json", [item.model_dump() for item in events])
            return event

    def get_events(self, run_id: str) -> list[TaskRunEvent]:
        data = self._read(self._run_dir(run_id) / "events.json") or []
        return [TaskRunEvent.model_validate(item) for item in data if isinstance(item, dict)]

    def save_result(self, run_id: str, result: TaskRunResult) -> TaskRunResult:
        self._write(self._run_dir(run_id) / "result.json", result.model_dump())
        self._cohere_terminal_result(run_id, result)
        return result

    def get_result(self, run_id: str) -> TaskRunResult | None:
        result = self._read_result_model(run_id)
        if result is not None:
            return result
        index = self.get_run_index(run_id)
        if isinstance(index, dict) and str(index.get("status") or "") in self._terminal_statuses():
            return self.ensure_terminal_result(run_id)
        return None

    def _read_result_model(self, run_id: str) -> TaskRunResult | None:
        data = self._read(self._run_dir(run_id) / "result.json")
        return TaskRunResult.model_validate(data) if data else None

    def ensure_terminal_result(
        self,
        run_id: str,
        *,
        reason_code: str | None = None,
        summary: str | None = None,
    ) -> TaskRunResult | None:
        """Persist a conservative TaskRunResult for a terminal run that lacks one.

        This is a lifecycle guard, not a success path. It preserves already
        recorded artifact summaries and keeps reporting unsafe unless a normal
        runtime result explicitly completed successfully.
        """
        existing = self._read_result_model(run_id)
        if existing is not None:
            return existing
        run = self.get_run(run_id)
        if run is None or str(run.status) not in self._terminal_statuses():
            return None
        result_status = str(run.status)
        if result_status == "expired":
            result_status = "blocked"
        run_reason = self._terminal_reason_code(run)
        event_reason = self._terminal_event_reason_code(run_id)
        if reason_code:
            terminal_reason = reason_code
        elif event_reason == "TASKRUN_LIFECYCLE_TIMEOUT" and run_reason != "TASKRUN_LIFECYCLE_TIMEOUT":
            terminal_reason = run_reason
        else:
            terminal_reason = event_reason or run_reason
        artifacts = [item for item in run.produced_artifacts if isinstance(item, dict)]
        artifact_state = self._terminal_artifact_state(artifacts, reason_code=terminal_reason)
        semantic_result = self._try_semantic_terminal_result(
            run,
            artifacts=artifacts,
            artifact_state=artifact_state,
        )
        if semantic_result is not None:
            saved = self.save_result(run_id, semantic_result)
            terminal_event = self._first_terminal_event(run_id)
            semantic_reason = (
                saved.validation.get("reason_code")
                if isinstance(saved.validation, dict)
                else "SEMANTIC_RESULT_PERSISTED"
            )
            if terminal_event is None:
                self.append_event(
                    run_id,
                    TaskRunEvent(
                        event_id=f"task_run_event_{uuid4().hex}",
                        run_id=run_id,
                        sequence=len(self.get_events(run_id)) + 1,
                        type=self._terminal_event_type_for_result(saved.status),
                        status=saved.status,
                        message=saved.summary,
                        metadata={
                            "reason_code": semantic_reason,
                            "source": "phase_semantic_completion_policy",
                            "semantic_result_finalization": "completed",
                        },
                    ),
                )
            return saved
        validation_status = "passed" if result_status == "completed" and artifact_state.get("safe_to_use") is True else "blocked"
        completion_status = (
            "completed"
            if result_status == "completed" and validation_status == "passed"
            else "cancelled"
            if result_status == "cancelled"
            else "failed"
            if result_status == "failed"
            else "blocked"
        )
        result = TaskRunResult(
            run_id=run_id,
            status=result_status if result_status in {"completed", "partial", "failed", "cancelled", "blocked"} else "blocked",
            reason_code=None if result_status == "completed" else terminal_reason,
            summary=summary
            or (
                "TaskRun reached a terminal state without a persisted result; a conservative terminal result was finalized."
                if result_status != "completed"
                else "TaskRun completed without a persisted result; terminal result was finalized from recorded state."
            ),
            outputs={
                "terminal_result_finalization": {
                    "reason_code": terminal_reason,
                    "source": "task_run_store",
                    "finalized_from_terminal_run": True,
                    "safe_to_report_success": False,
                },
                "artifact_result": {
                    "artifact_ids": [str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")],
                    "logical_paths": list(
                        dict.fromkeys(
                            str(item.get("logical_path") or (item.get("metadata") or {}).get("logical_path") or "")
                            for item in artifacts
                            if item.get("logical_path") or (isinstance(item.get("metadata"), dict) and (item.get("metadata") or {}).get("logical_path"))
                        )
                    ),
                    "artifacts": artifacts,
                    "artifact_state": artifact_state,
                },
                "validation_result": {
                    "status": validation_status,
                    "reason_code": terminal_reason,
                    "safe_to_report_success": False,
                    "safe_to_continue": False,
                    "blocking_findings": [] if validation_status == "passed" else [terminal_reason],
                },
            },
            warnings=["terminal_result_missing_repaired"],
            blocked_items=[] if validation_status == "passed" else [terminal_reason],
            events_count=len(self.get_events(run_id)),
            trace_ref=f"task-runs/{run_id}/trace",
            validation={
                "status": validation_status,
                "score": 1.0 if validation_status == "passed" else 0.0,
                "safe_to_display": True,
                "safe_to_report_success": False,
                "blocking_findings": [] if validation_status == "passed" else [terminal_reason],
                "reason_code": terminal_reason,
            },
            completion=TaskCompletionEvaluation(
                status=completion_status,  # type: ignore[arg-type]
                safe_to_report_success=False,
                missing_outcomes=[] if completion_status == "completed" else [terminal_reason],
                warnings=["terminal_result_missing_repaired"],
                limitations=[] if completion_status == "completed" else ["terminal_result_finalized_conservatively"],
                metadata={
                    "reason_code": terminal_reason,
                    "source": "task_run_store",
                    "artifact_state": artifact_state,
                },
            ),
        )
        saved = self.save_result(run_id, result)
        if self._first_terminal_event(run_id) is None:
            self.append_event(
                run_id,
                TaskRunEvent(
                    event_id=f"task_run_event_{uuid4().hex}",
                    run_id=run_id,
                    sequence=len(self.get_events(run_id)) + 1,
                    type=self._terminal_event_type_for_result(saved.status),
                    status=saved.status,
                    message=saved.summary,
                    metadata={"reason_code": terminal_reason, "source": "ensure_terminal_result"},
                ),
            )
        return saved

    def terminalize_if_runtime_budget_exceeded(
        self,
        run_id: str,
        *,
        max_runtime_seconds: float,
        reason_code: str = "TASKRUN_LIFECYCLE_TIMEOUT",
        record_ignored_attempt: bool = True,
    ) -> TaskRunResult | None:
        with self._terminal_event_lock:
            index = self.get_run_index(run_id)
            if isinstance(index, dict) and str(index.get("status") or "") not in {"running", "queued", "created"}:
                ensured = self.ensure_terminal_result(run_id, reason_code=reason_code)
                if not record_ignored_attempt:
                    return ensured or self.get_result(run_id)
                terminal_event = self._first_terminal_event(run_id)
                self._append_terminalization_ignored(
                    run_id,
                    attempted_status="blocked",
                    reason_code=reason_code,
                    terminal_event=terminal_event,
                )
                return ensured or self.get_result(run_id)
            run = self.get_run(run_id)
            if run is None:
                return None
            terminal_event = self._first_terminal_event(run_id)
            if terminal_event is not None or run.status not in {"running", "queued", "created"}:
                ensured = self.ensure_terminal_result(run_id, reason_code=reason_code)
                self._append_terminalization_ignored(
                    run_id,
                    attempted_status="blocked",
                    reason_code=reason_code,
                    terminal_event=terminal_event,
                )
                return ensured or self.get_result(run_id)
            existing = self.get_result(run_id)
            if existing is not None:
                self._append_terminalization_ignored(
                    run_id,
                    attempted_status="blocked",
                    reason_code=reason_code,
                    terminal_event=terminal_event,
                )
                return existing
            started_at = self._runtime_started_at(run_id, run)
            if started_at is None:
                return None
            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
            if elapsed <= max_runtime_seconds:
                return None
            if self._artifact_creation_in_progress(run_id) is not None:
                artifact_result = self.terminalize_if_artifact_creation_stalled(
                    run_id,
                    max_silence_seconds=0,
                    reason_code="ARTIFACT_CREATION_TIMEOUT_WITHOUT_TERMINAL_ARTIFACT",
                    result_source="artifact_worker_terminalization_guard",
                )
                if artifact_result is not None:
                    return artifact_result
            artifacts = [item for item in run.produced_artifacts if isinstance(item, dict)]
            semantic_artifact_state = self._terminal_artifact_state(artifacts, reason_code=reason_code)
            semantic_result = self._try_semantic_terminal_result(
                run.model_copy(update={"status": "blocked", "finished_at": datetime.now(timezone.utc).isoformat()}),
                artifacts=artifacts,
                artifact_state=semantic_artifact_state,
            )
            if semantic_result is not None:
                run.status = "blocked"  # type: ignore[assignment]
                run.finished_at = semantic_result.finished_at or datetime.now(timezone.utc).isoformat()
                run.current_step_id = None
                semantic_reason = (
                    semantic_result.validation.get("reason_code")
                    if isinstance(semantic_result.validation, dict)
                    else semantic_result.outputs.get("terminal_result_finalization", {}).get("reason_code")
                )
                run.blocked_reasons = list(dict.fromkeys([*run.blocked_reasons, str(semantic_reason or "SEMANTIC_COMPLETION_FINALIZED")]))
                run.warnings = list(dict.fromkeys([*run.warnings, "store_repair_suppressed_due_to_semantic_artifact_state"]))
                run.revision += 1
                self.update_run(run)
                self.save_result(run_id, semantic_result)
                self.append_event(
                    run_id,
                    TaskRunEvent(
                        event_id=f"task_run_event_{uuid4().hex}",
                        run_id=run_id,
                        sequence=len(self.get_events(run_id)) + 1,
                        type=self._terminal_event_type_for_result(semantic_result.status),
                        status=semantic_result.status,
                        message=semantic_result.summary,
                        metadata={
                            "reason_code": semantic_reason,
                            "source": "phase_semantic_completion_policy",
                            "store_repair_suppressed_due_to_semantic_artifact_state": True,
                            "elapsed_seconds": round(elapsed, 3),
                            "max_runtime_seconds": max_runtime_seconds,
                        },
                    ),
                )
                return semantic_result
            run.status = "blocked"  # type: ignore[assignment]
            run.finished_at = datetime.now(timezone.utc).isoformat()
            run.current_step_id = None
            run.blocked_reasons = list(dict.fromkeys([*run.blocked_reasons, reason_code]))
            run.warnings = list(dict.fromkeys([*run.warnings, "runtime_budget_exceeded"]))
            run.revision += 1
            self.update_run(run)
            result = TaskRunResult(
                run_id=run_id,
                status="blocked",
                reason_code=reason_code,
                summary="TaskRun reached a governed runtime budget before producing a terminal result.",
                outputs={
                    "runtime_budget": {
                        "reason_code": reason_code,
                        "elapsed_seconds": round(elapsed, 3),
                        "max_runtime_seconds": max_runtime_seconds,
                        "terminal_reason": reason_code,
                        "server_completed": False,
                    }
                },
                warnings=["runtime_budget_exceeded"],
                blocked_items=[reason_code],
                validation={
                    "status": "blocked",
                    "safe_to_display": True,
                    "reason_code": reason_code,
                    "blocking_findings": [reason_code],
                },
                completion=TaskCompletionEvaluation(
                    status="blocked",
                    safe_to_report_success=False,
                    missing_outcomes=[reason_code],
                    warnings=["runtime_budget_exceeded"],
                    limitations=["task_run_runtime_budget_exceeded"],
                    metadata={
                        "reason_code": reason_code,
                        "elapsed_seconds": round(elapsed, 3),
                        "max_runtime_seconds": max_runtime_seconds,
                        "source": "task_run_store",
                    },
                ),
            )
            self.save_result(run_id, result)
            self.append_event(
                run_id,
                TaskRunEvent(
                    event_id=f"task_run_event_{uuid4().hex}",
                    run_id=run_id,
                    sequence=len(self.get_events(run_id)) + 1,
                    type="run_blocked",
                    status="blocked",
                    message="TaskRun blocked by governed runtime budget.",
                    metadata={
                        "reason_code": reason_code,
                        "elapsed_seconds": round(elapsed, 3),
                        "max_runtime_seconds": max_runtime_seconds,
                    },
                ),
            )
            return result

    def terminalize_if_artifact_creation_stalled(
        self,
        run_id: str,
        *,
        max_silence_seconds: float,
        reason_code: str = "ARTIFACT_CREATION_TIMEOUT_WITHOUT_TERMINAL_ARTIFACT",
        result_source: str = "artifact_worker_terminalization_guard",
    ) -> TaskRunResult | None:
        """Persist a terminal result for an active run stuck after artifact start."""
        with self._terminal_event_lock:
            existing = self._read_result_model(run_id)
            if existing is not None:
                return existing
            run = self.get_run(run_id)
            if run is None or str(run.status) not in {"created", "queued", "running"}:
                return None
            if self._first_terminal_event(run_id) is not None:
                return self.ensure_terminal_result(run_id, reason_code=reason_code)
            artifact_event = self._artifact_creation_in_progress(run_id)
            if artifact_event is None:
                return None
            elapsed_seconds = self._event_elapsed_seconds(artifact_event)
            last_checkpoint = self._last_artifact_render_checkpoint(run_id, artifact_event)
            checkpoint_silence_seconds = self._event_elapsed_seconds(last_checkpoint) if last_checkpoint is not None else elapsed_seconds
            if checkpoint_silence_seconds is None or checkpoint_silence_seconds < max(0.0, float(max_silence_seconds)):
                return None

            now = datetime.now(timezone.utc).isoformat()
            metadata = artifact_event.metadata or {}
            logical_path = str(metadata.get("logical_path") or "")
            producer_step = str(metadata.get("producer_step") or "readonly_analysis_artifact_runtime")
            last_checkpoint_metadata = last_checkpoint.metadata if last_checkpoint is not None and isinstance(last_checkpoint.metadata, dict) else {}
            reason_code = self._artifact_stall_reason_code(artifact_event, reason_code)
            artifact_row = self._stalled_artifact_row(
                logical_path=logical_path,
                producer_step=producer_step,
                reason_code=reason_code,
                source=result_source,
                created_event_source_id=artifact_event.event_id,
                elapsed_seconds=elapsed_seconds,
            )
            artifacts = [item for item in run.produced_artifacts if isinstance(item, dict)]
            if artifact_row and not self._has_artifact_for_logical_path(artifacts, logical_path):
                artifacts.append(artifact_row)
            self.append_event(
                run_id,
                TaskRunEvent(
                    event_id=f"task_run_event_{uuid4().hex}",
                    run_id=run_id,
                    sequence=len(self.get_events(run_id)) + 1,
                    type="artifact_failed",
                    status="blocked",
                    message="Artifact creation did not produce a terminal artifact state within the governed budget.",
                    metadata={
                        "source": result_source,
                        "reason_code": reason_code,
                        "logical_path": logical_path or None,
                        "producer_step": producer_step,
                        "created_event_source_id": artifact_event.event_id,
                        "elapsed_seconds": round(elapsed_seconds, 3),
                        "last_checkpoint_stage": last_checkpoint_metadata.get("stage"),
                        "last_checkpoint_sequence": getattr(last_checkpoint, "sequence", None),
                        "safe_to_use": False,
                    },
                ),
            )
            artifact_state = self._terminal_artifact_state(artifacts, reason_code=reason_code)
            validation = {
                "status": "blocked",
                "reason_code": reason_code,
                "safe_to_display": True,
                "safe_to_report_success": False,
                "safe_to_continue": False,
                "blocking_findings": [reason_code],
                "component": "artifact_worker_terminalization_guard",
                "frontier": "ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GAP",
            }
            completion = TaskCompletionEvaluation(
                status="blocked",
                safe_to_report_success=False,
                missing_outcomes=[reason_code],
                warnings=["artifact_creation_stall_terminalized"],
                limitations=["artifact_creation_started_without_terminal_artifact"],
                metadata={
                    "reason_code": reason_code,
                    "source": result_source,
                    "artifact_state": artifact_state,
                },
            )
            result = TaskRunResult(
                run_id=run_id,
                status="blocked",
                source=result_source,
                reason_code=reason_code,
                finished_at=now,
                summary="Artifact creation started but did not reach a terminal artifact state; the run was blocked conservatively.",
                outputs={
                    "artifact_worker_terminalization_guard": {
                        "reason_code": reason_code,
                        "source": result_source,
                        "artifact_terminal_state_missing": True,
                        "logical_path": logical_path or None,
                        "producer_step": producer_step,
                        "created_event_source_id": artifact_event.event_id,
                        "elapsed_seconds": round(elapsed_seconds, 3),
                        "last_checkpoint_stage": last_checkpoint_metadata.get("stage"),
                        "last_checkpoint_sequence": getattr(last_checkpoint, "sequence", None),
                        "safe_to_report_success": False,
                    },
                    "artifact_result": {
                        "artifact_ids": [str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")],
                        "logical_paths": [str(item.get("logical_path") or "") for item in artifacts if item.get("logical_path")],
                        "artifacts": artifacts,
                        "artifact_state": artifact_state,
                    },
                    "validation_result": validation,
                },
                warnings=["artifact_creation_stall_terminalized"],
                blocked_items=[reason_code],
                events_count=len(self.get_events(run_id)),
                trace_ref=f"task-runs/{run_id}/trace",
                validation=validation,
                completion=completion,
            )
            run.status = "blocked"  # type: ignore[assignment]
            run.finished_at = run.finished_at or now
            run.current_step_id = None
            run.produced_artifacts = artifacts
            run.blocked_reasons = list(dict.fromkeys([*run.blocked_reasons, reason_code]))
            run.warnings = list(dict.fromkeys([*run.warnings, "artifact_creation_stall_terminalized"]))
            run.revision += 1
            self.update_run(run)
            saved = self.save_result(run_id, result)
            self.append_event(
                run_id,
                TaskRunEvent(
                    event_id=f"task_run_event_{uuid4().hex}",
                    run_id=run_id,
                    sequence=len(self.get_events(run_id)) + 1,
                    type="run_blocked",
                    status="blocked",
                    message=saved.summary,
                    metadata={
                        "reason_code": reason_code,
                        "source": result_source,
                        "logical_path": logical_path or None,
                        "producer_step": producer_step,
                        "elapsed_seconds": round(elapsed_seconds, 3),
                        "last_checkpoint_stage": last_checkpoint_metadata.get("stage"),
                        "last_checkpoint_sequence": getattr(last_checkpoint, "sequence", None),
                    },
                ),
            )
            return saved

    def _terminal_event_types(self) -> set[str]:
        return {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}

    def _terminal_statuses(self) -> set[str]:
        return {"completed", "completed_with_limitations", "partial", "failed", "cancelled", "blocked", "expired"}

    def _terminal_event_type_for_result(self, status: str) -> str:
        return {
            "completed": "run_completed",
            "completed_with_limitations": "run_partial",
            "partial": "run_partial",
            "failed": "run_failed",
            "cancelled": "run_cancelled",
            "blocked": "run_blocked",
        }.get(status, "run_blocked")

    def _artifact_creation_in_progress(self, run_id: str) -> TaskRunEvent | None:
        for event in sorted(self.get_events(run_id), key=lambda item: item.sequence, reverse=True):
            if event.type == "artifact_creation_started" and not self._has_artifact_terminal_after(run_id, event):
                return event
        return None

    def _artifact_stall_reason_code(self, artifact_event: TaskRunEvent, fallback: str) -> str:
        metadata = artifact_event.metadata if isinstance(artifact_event.metadata, dict) else {}
        artifact_kind = str(metadata.get("artifact_kind") or "")
        contract_id = str(metadata.get("contract_id") or "")
        if artifact_kind == "media_corpus_inventory" or contract_id == "media_corpus_inventory_artifact":
            checkpoint = self._last_artifact_render_checkpoint(artifact_event.run_id, artifact_event)
            checkpoint_metadata = checkpoint.metadata if checkpoint is not None and isinstance(checkpoint.metadata, dict) else {}
            stage_reason = _MEDIA_INVENTORY_STAGE_STALL_REASONS.get(str(checkpoint_metadata.get("stage") or ""))
            if stage_reason:
                return stage_reason
            return "MUSIC_INVENTORY_ARTIFACT_STALLED_AFTER_CREATION_STARTED"
        return fallback

    def _last_artifact_render_checkpoint(self, run_id: str, artifact_event: TaskRunEvent) -> TaskRunEvent | None:
        artifact_metadata = artifact_event.metadata if isinstance(artifact_event.metadata, dict) else {}
        logical_path = str(artifact_metadata.get("logical_path") or "")
        artifact_attempt_id = str(artifact_metadata.get("artifact_attempt_id") or "")
        last = None
        for event in self.get_events(run_id):
            if event.sequence <= artifact_event.sequence or event.type != "artifact_render_checkpoint":
                continue
            metadata = event.metadata if isinstance(event.metadata, dict) else {}
            if artifact_attempt_id and str(metadata.get("artifact_attempt_id") or "") == artifact_attempt_id:
                last = event
                continue
            if logical_path and str(metadata.get("logical_path") or "") == logical_path:
                last = event
        return last

    def _has_artifact_terminal_after(self, run_id: str, artifact_event: TaskRunEvent) -> bool:
        metadata = artifact_event.metadata or {}
        logical_path = str(metadata.get("logical_path") or "")
        terminal_types = {
            "artifact_created",
            "artifact_partial",
            "artifact_blocked",
            "artifact_failed",
            "artifact_interrupted",
            "artifact_late_rejected",
        }
        for event in self.get_events(run_id):
            if event.sequence <= artifact_event.sequence or event.type not in terminal_types:
                continue
            event_metadata = event.metadata or {}
            source_id = event_metadata.get("created_event_source_id")
            event_logical_path = str(event_metadata.get("logical_path") or "")
            if source_id == artifact_event.event_id or (logical_path and event_logical_path == logical_path):
                return True
        return False

    def _event_elapsed_seconds(self, event: TaskRunEvent) -> float | None:
        try:
            timestamp = str(event.timestamp or "")
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            started = datetime.fromisoformat(timestamp)
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - started).total_seconds()
        except Exception:
            return None

    def _stalled_artifact_row(
        self,
        *,
        logical_path: str,
        producer_step: str,
        reason_code: str,
        source: str,
        created_event_source_id: str,
        elapsed_seconds: float,
    ) -> dict[str, Any] | None:
        if not logical_path:
            return None
        return {
            "logical_path": logical_path,
            "status": "blocked",
            "reason_code": reason_code,
            "source": source,
            "producer_step": producer_step,
            "created_event_source_id": created_event_source_id,
            "semantic_contract_status": "not_evaluated",
            "safe_to_use": False,
            "safe_to_report_success": False,
            "artifact_terminal_state_missing": True,
            "elapsed_seconds": round(elapsed_seconds, 3),
        }

    def _has_artifact_for_logical_path(self, artifacts: list[dict[str, Any]], logical_path: str) -> bool:
        if not logical_path:
            return False
        return any(str(item.get("logical_path") or "") == logical_path for item in artifacts)

    def _try_semantic_terminal_result(
        self,
        run: TaskRun,
        *,
        artifacts: list[dict[str, Any]],
        artifact_state: dict[str, Any],
    ) -> TaskRunResult | None:
        finalizer = PhaseSemanticResultFinalizer()
        if not finalizer.can_finalize(artifacts):
            return None
        try:
            return finalizer.build_result(
                run=run,
                artifacts=artifacts,
                artifact_state=artifact_state,
                events_count=len(self.get_events(run.run_id)),
                finished_at=run.finished_at,
            )
        except Exception as exc:
            reason = "SEMANTIC_COMPLETION_RESULT_FINALIZATION_FAILED"
            logical_paths = list(
                dict.fromkeys(
                    str(item.get("logical_path") or (item.get("metadata") or {}).get("logical_path") or "")
                    for item in artifacts
                    if item.get("logical_path") or (isinstance(item.get("metadata"), dict) and (item.get("metadata") or {}).get("logical_path"))
                )
            )
            return TaskRunResult(
                run_id=run.run_id,
                status="blocked",
                source="phase_semantic_completion_policy",
                reason_code=reason,
                finished_at=run.finished_at or datetime.now(timezone.utc).isoformat(),
                summary="Semantic completion result finalization failed safely.",
                outputs={
                    "terminal_result_finalization": {
                        "reason_code": reason,
                        "source": "phase_semantic_completion_policy",
                        "semantic_result_finalization": "failed",
                        "safe_to_report_success": False,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    },
                    "artifact_result": {
                        "artifact_ids": [str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")],
                        "logical_paths": logical_paths,
                        "artifacts": artifacts,
                        "artifact_state": artifact_state,
                    },
                    "validation_result": {
                        "status": "blocked",
                        "reason_code": reason,
                        "safe_to_report_success": False,
                        "safe_to_continue": False,
                        "blocking_findings": [reason],
                    },
                },
                warnings=["semantic_completion_result_finalization_failed"],
                blocked_items=[reason],
                events_count=len(self.get_events(run.run_id)),
                trace_ref=f"task-runs/{run.run_id}/trace",
                validation={
                    "status": "blocked",
                    "score": 0.0,
                    "safe_to_display": True,
                    "safe_to_report_success": False,
                    "reason_code": reason,
                    "blocking_findings": [reason],
                },
                completion=TaskCompletionEvaluation(
                    status="blocked",
                    safe_to_report_success=False,
                    missing_outcomes=[reason],
                    warnings=["semantic_completion_result_finalization_failed"],
                    limitations=["semantic_completion_result_finalization_failed_safely"],
                    metadata={"reason_code": reason, "source": "phase_semantic_completion_policy"},
                ),
            )

    def _terminal_reason_code(self, run: TaskRun) -> str:
        artifact_reasons: list[str] = []
        for artifact in run.produced_artifacts:
            if not isinstance(artifact, dict):
                continue
            reason = artifact.get("reason_code")
            if not reason and isinstance(artifact.get("metadata"), dict):
                reason = (artifact.get("metadata") or {}).get("reason_code")
            if reason:
                artifact_reasons.append(str(reason))
        if artifact_reasons and all(str(reason) == "TASKRUN_LIFECYCLE_TIMEOUT" for reason in run.blocked_reasons if reason):
            return artifact_reasons[0]
        for reason in run.blocked_reasons:
            if reason:
                return str(reason)
        if artifact_reasons:
            return artifact_reasons[0]
        return "TERMINAL_RESULT_MISSING"

    def _terminal_event_reason_code(self, run_id: str) -> str | None:
        terminal = self._first_terminal_event(run_id)
        if terminal is None:
            return None
        metadata = terminal.metadata if isinstance(terminal.metadata, dict) else {}
        reason = metadata.get("reason_code")
        return str(reason) if reason else None

    def _terminal_artifact_state(self, artifacts: list[dict[str, Any]], *, reason_code: str) -> dict[str, Any]:
        if not artifacts:
            return {"status": "none", "count": 0, "safe_to_use": False, "reason_code": reason_code}
        unsafe = []
        for item in artifacts:
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            status = str(item.get("status") or metadata.get("status") or "")
            safe = item.get("safe_to_use") if "safe_to_use" in item else metadata.get("safe_to_use")
            if status in {"partial", "blocked", "interrupted", "failed", "rejected", "late_rejected"} or safe is False:
                unsafe.append(item)
        status = "partial" if unsafe else "available"
        artifact_reason = reason_code
        if unsafe:
            first = unsafe[0]
            metadata = first.get("metadata") if isinstance(first.get("metadata"), dict) else {}
            artifact_reason = str(first.get("reason_code") or metadata.get("reason_code") or reason_code)
        return {
            "status": status,
            "count": len(artifacts),
            "artifact_ids": [str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")],
            "safe_to_use": not bool(unsafe),
            "reason_code": artifact_reason,
            "partial_or_interrupted": unsafe,
        }

    def _first_terminal_event(self, run_id: str) -> TaskRunEvent | None:
        for event in sorted(self.get_events(run_id), key=lambda item: item.sequence):
            if event.type in self._terminal_event_types():
                return event
        return None

    def _append_terminalization_ignored(
        self,
        run_id: str,
        *,
        attempted_status: str,
        reason_code: str,
        terminal_event: TaskRunEvent | None,
    ) -> None:
        if terminal_event is None:
            terminal_event = self._first_terminal_event(run_id)
        if terminal_event is None:
            return
        for event in self.get_events(run_id):
            if (
                event.type == "terminalization_already_applied"
                and (event.metadata or {}).get("terminal_event_id") == terminal_event.event_id
                and (event.metadata or {}).get("attempted_reason_code") == reason_code
            ):
                return
        self.append_event(
            run_id,
            TaskRunEvent(
                event_id=f"task_run_event_{uuid4().hex}",
                run_id=run_id,
                sequence=len(self.get_events(run_id)) + 1,
                type="terminalization_already_applied",
                status="ignored",
                message="Terminalization ignored because the TaskRun already has a terminal event.",
                metadata={
                    "terminal_event_id": terminal_event.event_id,
                    "terminal_status": terminal_event.status,
                    "terminal_reason_code": (terminal_event.metadata or {}).get("reason_code"),
                    "attempted_status": attempted_status,
                    "attempted_reason_code": reason_code,
                    "ignored": True,
                    "reason": "terminal_state_already_set",
                },
            ),
        )

    def save_trace(self, run_id: str, trace: list[TaskRunTraceItem]) -> None:
        self._write(self._run_dir(run_id) / "trace.json", [item.model_dump() for item in trace])

    def get_trace(self, run_id: str) -> list[TaskRunTraceItem]:
        data = self._read(self._run_dir(run_id) / "trace.json") or []
        return [TaskRunTraceItem.model_validate(item) for item in data if isinstance(item, dict)]

    def sanitize(self, value: Any, *, key: str = "") -> Any:
        if key.lower() in _SENSITIVE_KEYS:
            return "[omitted_by_task_run_store]"
        if isinstance(value, dict):
            return {str(k): self.sanitize(v, key=str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            redacted = _SECRET.sub("[REDACTED]", value)
            return redacted[:30000]
        return value

    def light_summary(self, value: Any) -> Any:
        """Return a public/API-safe summary without loading nested evidence rows."""
        sanitized = self.sanitize(value)
        return self._lighten_for_inline(sanitized, run_dir=None)

    def _run_dir(self, run_id: str) -> Path:
        if not re.fullmatch(r"task_run_[a-f0-9]+", run_id):
            raise ValueError("invalid_task_run_id")
        return resolve_within_root(self.root / run_id, self.root)

    def _write_run_index(self, run: TaskRun) -> None:
        payload = {
            "run_id": run.run_id,
            "task_id": run.task_id,
            "task_run_id": run.task_run_id,
            "operation_id": run.operation_id,
            "session_id": run.session_id,
            "workspace": run.workspace,
            "contract_type": run.contract_type,
            "operation_type": run.operation_type,
            "runtime_profile": run.runtime_profile,
            "draft_id": run.draft_id,
            "approval_id": run.approval_id,
            "status": run.status,
            "current_phase": run.current_phase,
            "current_step_id": run.current_step_id,
            "auto_run_requested": run.auto_run_requested,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "revision": run.revision,
        }
        self._write(self._run_dir(run.run_id) / "run_index.json", payload)

    def _write_run_index_from_data(self, run_id: str, data: dict[str, Any]) -> None:
        payload = {
            "run_id": run_id,
            "task_id": data.get("task_id"),
            "task_run_id": data.get("task_run_id"),
            "operation_id": data.get("operation_id"),
            "session_id": data.get("session_id"),
            "workspace": data.get("workspace"),
            "contract_type": data.get("contract_type"),
            "operation_type": data.get("operation_type"),
            "runtime_profile": data.get("runtime_profile"),
            "draft_id": data.get("draft_id"),
            "approval_id": data.get("approval_id"),
            "status": data.get("status"),
            "current_phase": data.get("current_phase"),
            "current_step_id": data.get("current_step_id"),
            "auto_run_requested": data.get("auto_run_requested"),
            "created_at": data.get("created_at"),
            "started_at": data.get("started_at"),
            "finished_at": data.get("finished_at"),
            "revision": data.get("revision"),
        }
        self._write(self._run_dir(run_id) / "run_index.json", payload)

    def _write(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.sanitize(value)
        if path.name in {"run.json", "result.json", "events.json"}:
            payload = self._lighten_for_inline(payload, run_dir=path.parent)
        tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        encoded = json.dumps(payload, ensure_ascii=False, indent=2)
        with self._write_lock:
            tmp_path.write_text(encoded, encoding="utf-8")
            last_exc: PermissionError | None = None
            for attempt in range(5):
                try:
                    tmp_path.replace(path)
                    break
                except PermissionError as exc:
                    last_exc = exc
                    time.sleep(0.02 * (attempt + 1))
            else:
                try:
                    tmp_path.unlink(missing_ok=True)
                finally:
                    if last_exc is not None:
                        raise last_exc

    def _read(self, path: Path) -> Any:
        if not path.exists():
            return None
        last_exc: OSError | None = None
        for attempt in range(4):
            try:
                raw = path.read_text(encoding="utf-8-sig")
                break
            except PermissionError as exc:
                last_exc = exc
                time.sleep(0.01 * (attempt + 1))
        else:
            if last_exc is not None:
                raise last_exc
            return None
        if not raw.strip():
            return None
        return json.loads(raw)

    def _read_task_run(self, run_id: str) -> Any:
        run_dir = self._run_dir(run_id)
        data = self._read(run_dir / "run.json")
        if not isinstance(data, dict):
            return data
        return self._hydrate_payload_refs(data, run_dir=run_dir)

    def _hydrate_payload_refs(self, value: Any, *, run_dir: Path) -> Any:
        if isinstance(value, dict):
            if self._is_spilled_payload_ref(value):
                hydrated = self._read_payload_ref(value.get("content_ref"), run_dir=run_dir)
                if hydrated is not None:
                    return hydrated
                return value
            return {str(k): self._hydrate_payload_refs(v, run_dir=run_dir) for k, v in value.items()}
        if isinstance(value, list):
            return [self._hydrate_payload_refs(item, run_dir=run_dir) for item in value]
        return value

    def _project_payload_refs_for_model(self, value: Any) -> Any:
        if isinstance(value, dict):
            if self._is_spilled_payload_ref(value):
                summary = value.get("summary") if isinstance(value.get("summary"), dict) else {}
                summary_type = str(summary.get("type") or "")
                if summary_type == "list":
                    return []
                if summary_type == "dict":
                    return {}
                return None
            return {str(k): self._project_payload_refs_for_model(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._project_payload_refs_for_model(item) for item in value]
        return value

    def _is_spilled_payload_ref(self, value: dict[str, Any]) -> bool:
        return (
            isinstance(value.get("content_ref"), str)
            and value.get("reason_code") == "RUNTIME_PAYLOAD_SPILLED_TO_REF"
            and isinstance(value.get("hash"), str)
        )

    def _read_payload_ref(self, content_ref: Any, *, run_dir: Path) -> Any:
        try:
            return self.payload_refs.read_payload_ref(content_ref, run_id=run_dir.name)
        except Exception:
            return None

    def _cohere_terminal_result(self, run_id: str, result: TaskRunResult) -> None:
        terminal = {"completed", "partial", "failed", "cancelled", "blocked"}
        if result.status not in terminal:
            return
        path = self._run_dir(run_id) / "run.json"
        data = self._read(path)
        if not isinstance(data, dict):
            return
        if data.get("status") != result.status:
            data["status"] = result.status
        if not data.get("finished_at"):
            data["finished_at"] = datetime.now(timezone.utc).isoformat()
        data["current_step_id"] = None
        data["revision"] = int(data.get("revision") or 0) + 1
        self._write(path, data)
        self._write_run_index_from_data(run_id, data)

    def _runtime_started_at(self, run_id: str, run: TaskRun) -> datetime | None:
        candidates = [run.started_at]
        for event in self.get_events(run_id):
            if event.type in {"run_started", "project_analysis_started"}:
                candidates.append(event.timestamp)
        for value in candidates:
            if not value:
                continue
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except Exception:
                continue
        return None

    def _lighten_for_inline(self, value: Any, *, run_dir: Path | None, key: str = "", path: str = "") -> Any:
        if isinstance(value, dict):
            if key in _HEAVY_RUNTIME_KEYS and self._should_spill(value):
                return self._spill_or_summary(value, run_dir=run_dir, path=path, key=key)
            return {
                str(k): self._lighten_for_inline(v, run_dir=run_dir, key=str(k), path=f"{path}/{k}" if path else str(k))
                for k, v in value.items()
            }
        if isinstance(value, list):
            if key in _HEAVY_RUNTIME_KEYS and self._should_spill(value):
                return self._spill_or_summary(value, run_dir=run_dir, path=path, key=key)
            return [
                self._lighten_for_inline(item, run_dir=run_dir, key=key, path=f"{path}[{index}]")
                for index, item in enumerate(value)
            ]
        return value

    def _should_spill(self, value: Any) -> bool:
        if isinstance(value, list) and len(value) > 100:
            return True
        try:
            size = len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))
        except Exception:
            return False
        return size > 250_000

    def _spill_or_summary(self, value: Any, *, run_dir: Path | None, path: str, key: str) -> dict[str, Any]:
        if run_dir is not None:
            return self.payload_refs.write_payload_ref(run_id=run_dir.name, key=key, path=path, value=value)
        encoded = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return {
            "content_ref": None,
            "hash": digest,
            "sha256": digest,
            "size_bytes": len(encoded),
            "record_count": len(value) if isinstance(value, list) else len(value) if isinstance(value, dict) else None,
            "reason_code": "RUNTIME_PAYLOAD_SUMMARIZED_FOR_INLINE_VIEW",
            "path": path,
            "key": key,
            "summary": self._payload_summary(value),
        }

    def _payload_summary(self, value: Any) -> dict[str, Any]:
        if isinstance(value, list):
            return {
                "type": "list",
                "count": len(value),
                "sample": [self._light_row(item) for item in value[:10]],
            }
        if isinstance(value, dict):
            return {
                "type": "dict",
                "keys": sorted(str(k) for k in value.keys())[:50],
                "counts": {
                    str(k): len(v)
                    for k, v in value.items()
                    if isinstance(v, (list, dict))
                },
            }
        return {"type": type(value).__name__}

    def _light_row(self, item: Any) -> Any:
        if not isinstance(item, dict):
            return item
        allowed = {
            "artifact_id",
            "logical_path",
            "status",
            "validation_status",
            "content_type",
            "size_bytes",
            "sha256",
            "entity_id",
            "canonical_key",
            "attribute_name",
            "capability_id",
            "backend_id",
            "confidence",
            "observation_state",
            "gap_type",
            "reason_code",
        }
        return {key: value for key, value in item.items() if key in allowed}

    def status(self) -> dict[str, object]:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return {"status": "ok", "service": "task_run_store", "path": str(self.root), "sanitize_before_save": True, "raw_content_saved": False}
        except Exception as exc:
            return {"status": "degraded", "service": "task_run_store", "error": str(exc)}
