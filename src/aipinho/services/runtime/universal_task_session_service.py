from __future__ import annotations

import re
import os
from typing import Any

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.runtime.universal_task_session import (
    UniversalTaskApprovalState,
    UniversalTaskArtifactState,
    UniversalTaskProgress,
    UniversalTaskResultState,
    UniversalTaskSession,
    UniversalTaskStatus,
    UniversalTaskValidationState,
)
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.runtime_timeline_service import RuntimeTimelineService
from aipinho.services.runtime.runtime_truth_engine import RuntimeTruthEngine
from aipinho.services.runtime.canonical_operation_state_service import CanonicalOperationStateService
from aipinho.schemas.runtime.canonical_operation_state import CanonicalOperationState
from aipinho.services.cvl.cognitive_readiness_service import CognitiveReadinessService


_TERMINAL_STATUSES = {"completed", "partial", "failed", "blocked", "cancelled", "expired"}
_COMPLETED_STEP_STATUSES = {"completed", "skipped"}
_ARTIFACT_ACTION_MARKERS = ("artifact", "report", "zip", "export")
_ARTIFACT_ID_PATTERN = re.compile(r"\b(?:artifact|agent_artifact)_[A-Za-z0-9_:-]+\b")


class UniversalTaskSessionService:
    """Public governed view over TaskRun runtime state.

    This service deliberately does not execute anything. It only aggregates the
    canonical runtime stores into one client-neutral task session protocol.
    """

    def __init__(
        self,
        *,
        store: TaskRunStore | None = None,
        approvals: ApprovalService | None = None,
        artifacts: ArtifactRuntimeService | None = None,
    ) -> None:
        self.store = store or TaskRunStore()
        self.approvals = approvals or ApprovalService()
        self.artifacts = artifacts or ArtifactRuntimeService()
        self.timelines = RuntimeTimelineService(store=self.store, artifacts=self.artifacts)
        self.truth = RuntimeTruthEngine()
        self.canonical_states = CanonicalOperationStateService()

    def get_session(self, run_id: str) -> UniversalTaskSession | None:
        run = self.store.get_run_lightweight(run_id)
        if run is None:
            return None
        result = self._result_for_public_projection(run_id, run)
        events = self.store.get_events(run_id)
        artifact_rows = self._artifacts_for(run, result)
        terminal_blocked = str(run.status or "") in {"blocked", "failed", "cancelled", "expired"}
        timeline = None if terminal_blocked else self.timelines.build(run_id)
        truth = self.truth.evaluate(run, result=result, timeline=timeline)
        canonical = self.canonical_states.derive(run, result=result, truth=truth, artifacts=artifact_rows)
        workspace_context = getattr(run, "workspace_context", None)
        retrieval_context = getattr(run, "retrieval_context", None)
        execution_context = getattr(run, "execution_context", None)
        return UniversalTaskSession(
            task_run_id=run.run_id,
            public_id=run.run_id,
            status=self._status_from_canonical(canonical.status),
            phase=truth.phase,
            progress=self._progress(run, result),
            eta=None,
            started_at=run.started_at,
            updated_at=self._updated_at(run, events),
            current_step=run.current_step_id,
            approval_state=self._approval_state(run),
            validation_state=self._validation_state(run, result, canonical=canonical),
            artifact_state=self._artifact_state(run, result, artifact_rows),
            result_state=self._result_state(run, result, canonical=canonical),
            events_count=len(events),
            links={
                "self": f"/api/v1/task_runs/{run.run_id}",
                "events": f"/api/v1/task_runs/{run.run_id}/events",
                "timeline": f"/api/v1/task_runs/{run.run_id}/timeline",
                "artifacts": f"/api/v1/task_runs/{run.run_id}/artifacts",
                "summary": f"/api/v1/task_runs/{run.run_id}/summary",
                "legacy_trace": f"/api/v1/task-runs/{run.run_id}/trace",
            },
            warnings=list(run.warnings),
            blocked_reasons=list(run.blocked_reasons),
            metadata={
                "task_id": run.task_id or run.run_id,
                "task_run_id": run.run_id,
                "operation_id": run.operation_id,
                "workspace_id": run.workspace_id,
                "project_id": run.project_id,
                "parent_task_id": run.parent_task_id,
                "current_sprint": run.current_sprint,
                "current_phase": run.current_phase,
                "bootstrap_context": run.bootstrap_context,
                "source_type": run.source_type,
                "session_id": run.session_id,
                "workspace": run.workspace,
                "contract_type": run.contract_type,
                "operation_type": run.operation_type,
                "runtime_profile": run.runtime_profile,
                "requested_actions": list(run.requested_actions),
                "canonical_source": "task_run_store",
                "timeline_source": "not_loaded_for_terminal_block" if timeline is None else "runtime_timeline_service",
                "runtime_truth": truth.model_dump(mode="json"),
                "canonical_operation_state": canonical.model_dump(mode="json"),
                "workspace_context": workspace_context.model_dump(mode="json") if workspace_context is not None else None,
                "retrieval_context": retrieval_context.model_dump(mode="json") if retrieval_context is not None else None,
                "execution_context": execution_context.model_dump(mode="json") if execution_context is not None else None,
                "canonical_runtime_context": self._canonical_runtime_context(
                    workspace_context=workspace_context,
                    retrieval_context=retrieval_context,
                    execution_context=execution_context,
                ),
                "raw_default_visible": False,
            },
        )

    def _result_for_public_projection(self, run_id: str, run: TaskRun) -> TaskRunResult | None:
        result = self.store.get_result(run_id)
        if result is not None:
            return result
        if str(run.status or "") in _TERMINAL_STATUSES:
            return self.store.ensure_terminal_result(run_id)
        return None

    def list_sessions(
        self,
        *,
        status: str | None = None,
        session_id: str | None = None,
        contract_type: str | None = None,
        limit: int = 100,
    ) -> list[UniversalTaskSession]:
        runs = self.store.list_runs(
            status=status,
            session_id=session_id,
            contract_type=contract_type,
            limit=limit,
        )
        sessions: list[UniversalTaskSession] = []
        for run in runs:
            session = self.get_session(run.run_id)
            if session is not None:
                sessions.append(session)
        return sessions

    def events(self, run_id: str, *, after_sequence: int | None = None, limit: int = 200) -> dict[str, Any] | None:
        self._apply_runtime_budget_supervision(run_id)
        run = self.store.get_run_lightweight(run_id)
        if run is None:
            return None
        rows = self.store.get_events(run_id)
        total_count = len(rows)
        if after_sequence is not None:
            rows = [event for event in rows if event.sequence > after_sequence]
        effective_limit = max(1, min(limit, 1000))
        page = rows[:effective_limit]
        next_cursor = page[-1].sequence if len(rows) > len(page) and page else None
        return {
            "task_run_id": run_id,
            "events": [event.model_dump() for event in page],
            "count": len(page),
            "event_count_total": total_count,
            "events_truncated": len(rows) > len(page),
            "next_cursor": next_cursor,
            "source": "task_run_store",
        }

    def artifacts_for_run(self, run_id: str) -> dict[str, Any] | None:
        self._apply_runtime_budget_supervision(run_id)
        run = self.store.get_run_lightweight(run_id)
        if run is None:
            return None
        result = self._result_for_public_projection(run_id, run)
        rows = self._artifacts_for(run, result)
        return {
            "task_run_id": run_id,
            "artifact_state": self._artifact_state(run, result, rows).model_dump(),
            "artifacts": rows,
            "count": len(rows),
            "source": "artifact_runtime",
        }

    def summary(self, run_id: str) -> dict[str, Any] | None:
        self._apply_runtime_budget_supervision(run_id)
        run = self.store.get_run_lightweight(run_id)
        if run is None:
            return None
        result = self._result_for_public_projection(run_id, run)
        events = self.store.get_events(run_id)
        artifacts = self._artifacts_for(run, result)
        approval = self._approval_state(run)
        validation = self._validation_state(run, result)
        result_state = self._result_state(run, result)
        status = self._summary_status_from_states(
            run=run,
            result=result,
            approval_status=approval.status,
            validation_status=validation.status,
            result_status=result_state.status,
        )
        observational = self._observational_cognition_summary_from_artifacts(
            artifacts=artifacts,
            blocked=status == "BLOCKED" or validation.status == "blocked" or result_state.status == "blocked",
        )
        return {
            "task_run_id": run_id,
            "status": status,
            "finished_at": run.finished_at,
            "phase": self._phase(run, result),
            "progress": self._progress(run, result).model_dump(),
            "current_step": run.current_step_id,
            "approval": approval.model_dump(),
            "validation": validation.model_dump(),
            "artifacts": {
                "status": self._artifact_state(run, result, artifacts).status,
                "count": len(artifacts),
                "artifact_ids": [str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")],
            },
            "result": result_state.model_dump(),
            "project_analysis": self._project_analysis_summary(result),
            "public_response_boundary": self._public_response_boundary_summary(
                run=run,
                result=result,
                events=events,
                status=status,
                result_status=result_state.status,
            ),
            "observational_cognition": observational,
            "media_metadata_capability": observational.get("media_metadata_capability"),
            "relationship_cognition": observational.get("relationship_cognition"),
            "cognitive_readiness": self._cognitive_readiness_summary(run),
            "last_event": self._last_event_summary(run_id),
            "links": {
                "self": f"/api/v1/task_runs/{run.run_id}",
                "events": f"/api/v1/task_runs/{run.run_id}/events",
                "timeline": f"/api/v1/task_runs/{run.run_id}/timeline",
                "artifacts": f"/api/v1/task_runs/{run.run_id}/artifacts",
                "summary": f"/api/v1/task_runs/{run.run_id}/summary",
                "legacy_trace": f"/api/v1/task-runs/{run.run_id}/trace",
            },
        }

    def _public_response_boundary_summary(
        self,
        *,
        run: TaskRun,
        result: TaskRunResult | None,
        events: list[Any],
        status: str,
        result_status: str,
    ) -> dict[str, Any]:
        intent_boundary = run.intent_map.get("public_response_boundary") if isinstance(run.intent_map, dict) else {}
        bootstrap_boundary = (
            run.bootstrap_context.get("public_response_boundary") if isinstance(run.bootstrap_context, dict) else {}
        )
        boundary = intent_boundary if isinstance(intent_boundary, dict) and intent_boundary else bootstrap_boundary
        result_outputs = result.outputs if result is not None and isinstance(result.outputs, dict) else {}
        runtime_budget = result_outputs.get("runtime_budget") if isinstance(result_outputs.get("runtime_budget"), dict) else {}
        reason_codes = list(boundary.get("reason_codes") or []) if isinstance(boundary, dict) else []
        if result is not None:
            reason_codes.extend(str(item) for item in getattr(result, "blocked_items", []) or [])
            if runtime_budget.get("reason_code"):
                reason_codes.append(str(runtime_budget.get("reason_code")))
        reason_codes = list(dict.fromkeys(item for item in reason_codes if item))
        terminal_events = [event for event in events if getattr(event, "type", "") in {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}]
        public_status = str(boundary.get("status") or "").strip() if isinstance(boundary, dict) else ""
        if result_status == "completed" and run.status == "completed":
            public_status = "completed"
        elif result_status == "blocked" or run.status == "blocked":
            public_status = "timeout_blocked" if "PUBLIC_CHAT_RESPONSE_BUDGET_EXCEEDED" in reason_codes else "blocked"
        elif public_status != "accepted_running" and run.status in {"created", "queued", "running"}:
            public_status = "accepted_running" if boundary else "running"
        return {
            "status": public_status or status.casefold(),
            "client_response_budget_ms": boundary.get("client_response_budget_ms") if isinstance(boundary, dict) else None,
            "client_response_time_ms": boundary.get("client_response_time_ms") if isinstance(boundary, dict) else None,
            "continuation_available": bool(boundary.get("continuation_available")) if isinstance(boundary, dict) else run.status in {"queued", "running"},
            "polling_available": bool(boundary.get("polling_available")) if isinstance(boundary, dict) else True,
            "result_finalized": result is not None,
            "reason_codes": reason_codes,
            "terminal_event_count": len(terminal_events),
            "safe_to_report_success": bool(result_status == "completed" and run.status == "completed"),
        }

    def _project_analysis_summary(self, result: TaskRunResult | None) -> dict[str, Any] | None:
        if result is None or not isinstance(result.outputs, dict):
            return None
        payload = result.outputs.get("project_analysis_report")
        boundary = result.outputs.get("project_analysis_boundary")
        source = payload if isinstance(payload, dict) and payload else boundary if isinstance(boundary, dict) else None
        if not isinstance(source, dict):
            return None
        readiness = source.get("partial_readiness") if isinstance(source.get("partial_readiness"), dict) else {}
        return {
            "status": source.get("status") or source.get("project_analysis_status"),
            "reason_code": source.get("reason_code") or source.get("project_analysis_reason_code"),
            "safe_to_continue": source.get("safe_to_continue"),
            "files_discovered": source.get("files_discovered"),
            "files_selected": source.get("files_selected"),
            "files_read": source.get("files_read"),
            "files_partial_read": source.get("files_partial_read"),
            "files_skipped": source.get("files_skipped"),
            "bytes_read": source.get("bytes_read"),
            "bytes_skipped_estimated": source.get("bytes_skipped_estimated"),
            "read_decision_count": len(source.get("read_decisions") or []) if isinstance(source.get("read_decisions"), list) else 0,
            "read_decision_sample": list(source.get("read_decisions") or [])[:5] if isinstance(source.get("read_decisions"), list) else [],
            "remaining_budget_ms_at_return": source.get("remaining_budget_ms_at_return"),
            "handoff_reserve_reached": source.get("handoff_reserve_reached"),
            "partial_readiness": {
                "safe_to_continue_to_artifact_runtime": readiness.get("safe_to_continue_to_artifact_runtime"),
                "confidence": readiness.get("confidence"),
                "missing_context": list(readiness.get("missing_context") or [])[:20],
                "reason_codes": list(readiness.get("reason_codes") or [])[:20],
            },
        }

    def _apply_runtime_budget_supervision(self, run_id: str) -> None:
        try:
            max_runtime_seconds = float(os.environ.get("AIPINHO_PHASE1_MAX_RUNTIME_SECONDS", "900"))
        except Exception:
            max_runtime_seconds = 900.0
        try:
            self.store.terminalize_if_runtime_budget_exceeded(
                run_id,
                max_runtime_seconds=max_runtime_seconds,
                reason_code="TASKRUN_LIFECYCLE_TIMEOUT",
                record_ignored_attempt=False,
            )
        except Exception:
            return

    def _summary_status(self, session: UniversalTaskSession) -> UniversalTaskStatus:
        if (
            session.result_state.status == "blocked"
            and session.validation_state.status == "blocked"
            and session.approval_state.status in {"not_required", "none", "missing"}
        ):
            return "BLOCKED"
        return session.status

    def _summary_status_from_states(
        self,
        *,
        run: TaskRun,
        result: TaskRunResult | None,
        approval_status: str,
        validation_status: str,
        result_status: str,
    ) -> UniversalTaskStatus:
        if (
            result_status == "blocked"
            and validation_status == "blocked"
            and approval_status in {"not_required", "none", "missing"}
        ):
            return "BLOCKED"
        return self._status(run, result)

    def _status(self, run: TaskRun, result: TaskRunResult | None) -> UniversalTaskStatus:
        if result is not None:
            if result.status == "completed":
                return "COMPLETED"
            if result.status == "partial":
                return "COMPLETED"
            if result.status == "failed":
                return "FAILED"
            if result.status == "blocked":
                return "WAITING_APPROVAL" if self._approval_required_for(run) or run.approval_id else "BLOCKED"
            if result.status == "cancelled":
                return "CANCELLED"
        status = str(run.status or "").lower()
        if status == "created":
            return "CREATED"
        if status == "queued":
            return "QUEUED"
        if status == "waiting_delegation":
            return "WAITING_DELEGATION"
        if status == "waiting_input":
            return "WAITING_APPROVAL" if self._approval_required_for(run) or run.approval_id else "WAITING_USER"
        if status == "running":
            return "RUNNING"
        if status == "completed" or status == "partial":
            return "COMPLETED"
        if status == "failed":
            return "FAILED"
        if status == "blocked":
            return "WAITING_APPROVAL" if self._approval_required_for(run) or run.approval_id else "BLOCKED"
        if status == "cancelled":
            return "CANCELLED"
        if status == "expired":
            return "TIMEOUT"
        return "CREATED"

    def _status_from_truth(self, truth: Any) -> UniversalTaskStatus:
        status = str(getattr(truth, "status", "") or "").lower()
        if status == "completed" or status == "partial":
            return "COMPLETED"
        if status == "failed":
            return "FAILED"
        if status == "cancelled":
            return "CANCELLED"
        if status == "expired":
            return "TIMEOUT"
        if status == "blocked":
            return "BLOCKED"
        if status == "waiting_input":
            return "WAITING_APPROVAL"
        if status == "waiting_delegation":
            return "WAITING_DELEGATION"
        if status == "running":
            return "RUNNING"
        if status == "queued":
            return "QUEUED"
        return "CREATED"

    def _status_from_canonical(self, status: str) -> UniversalTaskStatus:
        mapping: dict[str, UniversalTaskStatus] = {
            "CREATED": "CREATED",
            "READY": "QUEUED",
            "RUNNING": "RUNNING",
            "WAITING_APPROVAL": "WAITING_APPROVAL",
            "WAITING_ARTIFACTS": "WAITING_USER",
            "VALIDATING": "RUNNING",
            "COMPLETED": "COMPLETED",
            "FAILED": "FAILED",
            "BLOCKED": "BLOCKED",
            "CANCELLED": "CANCELLED",
        }
        return mapping.get(str(status).upper(), "CREATED")

    def _phase(self, run: TaskRun, result: TaskRunResult | None) -> str:
        status = self._status(run, result)
        if status == "WAITING_APPROVAL":
            return "waiting_approval"
        if status == "WAITING_DELEGATION":
            return "waiting_delegation"
        if status in {"COMPLETED", "FAILED", "BLOCKED", "CANCELLED", "TIMEOUT"}:
            return status.lower()
        if status == "WAITING_USER":
            return "waiting_user"
        step = self._current_step(run)
        if step is not None:
            return str(step.step_type or step.action or "running")
        if status == "QUEUED":
            return "queued"
        return "unknown"

    def _progress(self, run: TaskRun, result: TaskRunResult | None) -> UniversalTaskProgress:
        if getattr(run, "workflow", None) is not None:
            phases = list(run.workflow.phases or [])
            completed = len([phase for phase in phases if phase.status in {"completed", "partial", "skipped"}])
            total = len(phases)
            return UniversalTaskProgress(
                percent=max(0, min(100, int(run.workflow.progress))),
                completed_units=completed,
                total_units=total,
                basis="workflow_phases",
                is_estimated=False,
            )
        steps = list(getattr(run.plan, "steps", []) or [])
        if not steps:
            percent = 100 if result is not None and result.status == "completed" else 0
            return UniversalTaskProgress(percent=percent, completed_units=int(percent == 100), total_units=int(percent == 100))
        completed = len([step for step in steps if step.status in _COMPLETED_STEP_STATUSES])
        total = len(steps)
        if result is not None and result.status == "completed":
            completed = total
        percent = int((completed / total) * 100) if total else 0
        return UniversalTaskProgress(
            percent=max(0, min(100, percent)),
            completed_units=completed,
            total_units=total,
            basis="task_run_plan_steps",
            is_estimated=False,
        )

    def _approval_state(self, run: TaskRun) -> UniversalTaskApprovalState:
        required = self._approval_required_for(run)
        approval_id = run.approval_id
        if not approval_id:
            return UniversalTaskApprovalState(
                status="not_required" if not required else "required_without_request",
                approval_id=None,
                required_actions=required,
                source="task_run_policy_snapshot",
            )
        approval = self.approvals.get_approval(approval_id)
        if approval is None:
            return UniversalTaskApprovalState(
                status="missing",
                approval_id=approval_id,
                required_actions=required,
                source="approval_store",
            )
        return UniversalTaskApprovalState(
            status=approval.status,
            approval_id=approval.approval_id,
            required_actions=list(approval.actions_requested or required),
            risk_level=approval.risk_level,
            expires_at=approval.expires_at,
            decided_at=getattr(approval, "decided_at", None),
            source="approval_store",
        )

    def _validation_state(
        self,
        run: TaskRun,
        result: TaskRunResult | None,
        *,
        canonical: CanonicalOperationState | None = None,
    ) -> UniversalTaskValidationState:
        if result is None:
            return UniversalTaskValidationState(status="not_started", safe_to_report_success=False)
        completion = result.completion
        missing = list(getattr(completion, "missing_outcomes", []) or [])
        safe_success = bool(getattr(completion, "safe_to_report_success", False))
        if run.status == "blocked" or result.status == "blocked":
            status = "blocked"
        elif missing:
            status = "incomplete"
        elif result.validation and isinstance(result.validation, dict):
            status = str(result.validation.get("status") or result.validation.get("validation_status") or result.status)
        else:
            status = "not_applicable" if result.status in {"cancelled", "blocked"} else result.status
        if canonical is not None:
            missing = list(dict.fromkeys([*missing, *canonical.missing_outputs]))
            safe_success = canonical.safe_to_report_success
            if canonical.status == "BLOCKED" and result.status == "completed":
                status = "blocked"
        return UniversalTaskValidationState(
            status=status,
            validation_id=str(result.validation.get("validation_id")) if isinstance(result.validation, dict) and result.validation.get("validation_id") else None,
            safe_to_report_success=safe_success and not missing and result.status == "completed",
            missing_outputs=missing,
            summary=result.summary,
            source="canonical_operation_state" if canonical is not None else "task_run_result",
        )

    def _artifact_state(self, run: TaskRun, result: TaskRunResult | None, artifacts: list[dict[str, Any]]) -> UniversalTaskArtifactState:
        artifact_ids = [str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")]
        required = self._artifact_required(run)
        result_artifact_state = self._result_artifact_state(result)
        unsafe_artifacts = [
            item
            for item in artifacts
            if str(item.get("status") or "") in {"partial", "blocked", "interrupted", "failed", "rejected", "late_rejected"}
            or item.get("safe_to_use") is False
        ]
        if artifacts:
            status = "partial" if unsafe_artifacts else "available"
        elif result_artifact_state.get("status"):
            status = str(result_artifact_state.get("status"))
        elif result is not None and required:
            status = "missing"
        elif required:
            status = "pending"
        else:
            status = "none"
        return UniversalTaskArtifactState(
            status=status,
            count=len(artifacts),
            artifact_ids=list(dict.fromkeys(artifact_ids)),
            artifacts=artifacts,
            reason_code=str(result_artifact_state.get("reason_code")) if result_artifact_state.get("reason_code") else None,
            terminal_phase=str((result.outputs.get("validation_result") or {}).get("phase")) if result and isinstance(result.outputs.get("validation_result"), dict) and (result.outputs.get("validation_result") or {}).get("phase") else None,
        )

    def _result_artifact_state(self, result: TaskRunResult | None) -> dict[str, Any]:
        if result is None:
            return {}
        artifact_result = result.outputs.get("artifact_result")
        if not isinstance(artifact_result, dict):
            return {}
        state = artifact_result.get("artifact_state")
        return state if isinstance(state, dict) else {}

    def _result_state(
        self,
        run: TaskRun,
        result: TaskRunResult | None,
        *,
        canonical: CanonicalOperationState | None = None,
    ) -> UniversalTaskResultState:
        cause = result.block_cause if result and result.block_cause else run.block_cause
        completion = result.completion if result else None
        missing = list(getattr(completion, "missing_outcomes", []) or [])
        safe_success = bool(getattr(completion, "safe_to_report_success", False))
        if result is None:
            return UniversalTaskResultState(
                status="pending" if run.status not in _TERMINAL_STATUSES else run.status,
                result_available=False,
                safe_to_report_success=False,
                block_reason_code=getattr(cause, "block_reason_code", None),
            )
        if canonical is not None:
            safe_success = canonical.safe_to_report_success
            missing = list(dict.fromkeys([*missing, *canonical.missing_outputs]))
            status = "blocked" if canonical.status == "BLOCKED" and result.status == "completed" else result.status
            reason = getattr(cause, "block_reason_code", None) or canonical.reason_code or self._result_block_reason_code(result)
        else:
            status = result.status
            reason = getattr(cause, "block_reason_code", None) or self._result_block_reason_code(result)
        return UniversalTaskResultState(
            status=status,
            summary=result.summary,
            safe_to_display=result.safe_to_display,
            safe_to_report_success=safe_success and not missing and result.status == "completed",
            result_available=True,
            block_reason_code=reason,
            source="canonical_operation_state" if canonical is not None else "task_run_result",
        )

    def _result_block_reason_code(self, result: TaskRunResult | None) -> str | None:
        if result is None or result.status != "blocked":
            return None
        if getattr(result, "reason_code", None):
            return str(result.reason_code)
        if isinstance(result.validation, dict):
            reason = result.validation.get("reason_code")
            if reason:
                return str(reason)
            findings = result.validation.get("blocking_findings")
            if isinstance(findings, list) and findings:
                return str(findings[0])
        if result.blocked_items:
            return str(result.blocked_items[0])
        artifact_state = self._result_artifact_state(result)
        reason = artifact_state.get("reason_code")
        return str(reason) if reason else None

    def _artifacts_for(self, run: TaskRun, result: TaskRunResult | None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            rows.extend(self._artifact_lookup_rows(run.run_id, limit=200))
        except Exception:
            rows = []
        known = {str(item.get("artifact_id")) for item in rows if item.get("artifact_id")}
        for artifact_id in self._artifact_ids_from_result(result):
            if artifact_id in known:
                continue
            try:
                record = self.artifacts.get(artifact_id)
            except Exception:
                record = None
            rows.append(record or {"artifact_id": artifact_id, "status": "unknown", "source": "task_run_result"})
            known.add(artifact_id)
        for artifact in self._artifact_rows_from_result(result):
            artifact_id = str(artifact.get("artifact_id") or "")
            logical_path = str(artifact.get("logical_path") or "")
            key = artifact_id or f"logical:{logical_path}:{artifact.get('status')}"
            if artifact_id and artifact_id in known:
                rows = [self._merge_artifact_runtime_state(row, artifact) for row in rows]
                continue
            if key in known:
                continue
            rows.append(artifact)
            known.add(key)
        return [self._light_artifact_row(item) for item in rows]

    def _merge_artifact_runtime_state(self, row: dict[str, Any], result_row: dict[str, Any]) -> dict[str, Any]:
        if str(row.get("artifact_id") or "") != str(result_row.get("artifact_id") or ""):
            return row
        merged = dict(row)
        for key in (
            "status",
            "validation_status",
            "reason_code",
            "semantic_contract_status",
            "semantic_contract_validation",
            "safe_to_use",
            "limitations",
            "partial_rows",
            "expected_rows",
            "selected_rows",
            "bound_rows",
            "evidence_ref_count",
            "evidence_refs",
            "evidence_refs_sample",
            "row_evidence_coverage",
            "row_validation_summary",
            "rendered_columns",
            "missing_columns",
            "metadata_coverage_summary",
            "inventory_sufficiency_summary",
            "use_safety",
            "visible_in_endpoint",
        ):
            value = result_row.get(key)
            if value not in (None, "", [], {}):
                merged[key] = value
        metadata = dict(merged.get("metadata") or {})
        result_metadata = result_row.get("metadata") if isinstance(result_row.get("metadata"), dict) else {}
        for key, value in result_metadata.items():
            if value not in (None, "", [], {}) and key not in metadata:
                metadata[key] = value
        if metadata:
            merged["metadata"] = metadata
        return merged

    def _artifact_rows_from_result(self, result: TaskRunResult | None) -> list[dict[str, Any]]:
        if result is None:
            return []
        artifact_result = result.outputs.get("artifact_result")
        if not isinstance(artifact_result, dict):
            return []
        rows = artifact_result.get("artifacts")
        if not isinstance(rows, list):
            return []
        return [item for item in rows if isinstance(item, dict)]

    def _light_artifact_row(self, artifact: dict[str, Any]) -> dict[str, Any]:
        row = dict(artifact)
        for coverage_key in ("schema_coverage",):
            coverage = row.get(coverage_key)
            if isinstance(coverage, dict):
                row[coverage_key] = self._light_schema_coverage(coverage)
        for container_key in ("metadata", "provenance"):
            container = row.get(container_key)
            if not isinstance(container, dict):
                continue
            updated = dict(container)
            coverage = updated.get("schema_coverage")
            if isinstance(coverage, dict):
                updated["schema_coverage"] = self._light_schema_coverage(coverage)
            declared = updated.get("declared_contract")
            if isinstance(declared, dict):
                updated["declared_contract"] = self.store.light_summary(declared)
            row[container_key] = updated
        return row

    def _light_schema_coverage(self, coverage: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "status": coverage.get("status"),
                "missing_columns": coverage.get("missing_columns"),
                "metadata_coverage_summary": coverage.get("metadata_coverage_summary"),
                "inventory_sufficiency_summary": coverage.get("inventory_sufficiency_summary"),
                "row_evidence_coverage": coverage.get("row_evidence_coverage"),
                "column_coverage": coverage.get("column_coverage"),
                "semantic_coverage": coverage.get("semantic_coverage"),
            }.items()
            if value not in (None, "", [], {})
        }

    def _artifact_lookup_rows(self, task_id: str, *, limit: int) -> list[dict[str, Any]]:
        lookup = self.artifacts.by_task(task_id, limit=limit)
        if isinstance(lookup, list):
            return lookup
        return list(getattr(lookup, "artifacts", []) or [])

    def _artifact_ids_from_result(self, result: TaskRunResult | None) -> list[str]:
        if result is None:
            return []
        ids: list[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if str(key) == "artifact_id" and item and self._looks_like_real_artifact_id(str(item)):
                        ids.append(str(item))
                    if str(key) == "artifact_ids" and isinstance(item, list):
                        ids.extend(str(candidate) for candidate in item if self._looks_like_real_artifact_id(str(candidate)))
                    visit(item)
                return
            if isinstance(value, list):
                for item in value:
                    visit(item)
                return

        visit(result.outputs)
        return list(dict.fromkeys(ids))

    def _looks_like_real_artifact_id(self, value: str) -> bool:
        if value in {"artifact_result", "artifact_runtime", "artifact_generation", "artifact_validation_failed"}:
            return False
        return bool(re.match(r"^(?:artifact|agent_artifact)_[A-Za-z0-9][A-Za-z0-9_:-]*$", value))

    def _approval_required_for(self, run: TaskRun) -> list[str]:
        policy = run.policy_snapshot if isinstance(run.policy_snapshot, dict) else {}
        return [str(item) for item in policy.get("approval_required_for", []) or []]

    def _artifact_required(self, run: TaskRun) -> bool:
        markers = " ".join([run.contract_type or "", run.operation_type or "", run.runtime_profile or "", *run.requested_actions]).lower()
        return any(marker in markers for marker in _ARTIFACT_ACTION_MARKERS)

    def _current_step(self, run: TaskRun):
        if not run.current_step_id:
            running = [step for step in run.plan.steps if step.status == "running"]
            return running[0] if running else None
        return next((step for step in run.plan.steps if step.step_id == run.current_step_id), None)

    def _updated_at(self, run: TaskRun, events: list[TaskRunEvent]) -> str | None:
        if events:
            return events[-1].timestamp
        return run.finished_at or run.started_at or run.created_at

    def _last_event_summary(self, run_id: str) -> dict[str, Any] | None:
        events = self.store.get_events(run_id)
        if not events:
            return None
        event = events[-1]
        return {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "type": event.type,
            "status": event.status,
            "message": event.message,
            "timestamp": event.timestamp,
        }

    def _cognitive_readiness_summary(self, run: TaskRun) -> dict[str, Any] | None:
        ref = run.intent_map.get("cognitive_readiness") if isinstance(run.intent_map.get("cognitive_readiness"), dict) else {}
        phase0_result_ref = str(ref.get("phase0_result_ref") or "") if isinstance(ref, dict) else ""
        readiness_id = str(ref.get("cognitive_readiness_id") or "") if isinstance(ref, dict) else ""
        if not phase0_result_ref and not readiness_id:
            return None
        try:
            return CognitiveReadinessService(store=self.store).lightweight_summary(
                readiness_ref=phase0_result_ref or readiness_id,
                task_run_id=run.run_id,
                runtime_executed_despite_no_go=bool(ref.get("runtime_executed_despite_cvl_no_go")) if isinstance(ref, dict) else False,
            )
        except Exception:
            return {
                "readiness_id": readiness_id or phase0_result_ref,
                "status": "unavailable",
            }

    def _observational_cognition_summary_from_artifacts(
        self,
        *,
        artifacts: list[dict[str, Any]],
        blocked: bool,
    ) -> dict[str, Any]:
        reports: list[dict[str, Any]] = []
        coverage2_reports: list[dict[str, Any]] = []
        semantic_gaps: list[dict[str, Any]] = []
        roots_scanned_by_role: dict[str, list[str]] = {}
        entities_by_root_role: dict[str, int] = {}
        entities_selected_by_artifact: dict[str, int] = {}
        entities_rejected_by_policy = 0
        workspace_role_mismatches = 0
        media_metadata_summaries: list[dict[str, Any]] = []
        evidence_total = 0
        evidence_by_attribute: dict[str, int] = {}
        goals_total = goals_blocked = goals_ready = 0
        knowledge_record_count = 0
        assertion_count = 0
        truth_eligible_assertion_count = 0
        self_review_summaries: list[dict[str, Any]] = []
        relationship_summaries: list[dict[str, Any]] = []
        relationship_bindings: list[dict[str, Any]] = []
        relationship_renderings: list[dict[str, Any]] = []
        metadata_coverage_summaries: list[dict[str, Any]] = []
        inventory_sufficiency_summaries: list[dict[str, Any]] = []
        for artifact in artifacts:
            logical_path = str(artifact.get("logical_path") or "")
            selected_rows = int(artifact.get("selected_rows") or 0)
            bound_rows = int(artifact.get("bound_rows") or artifact.get("partial_rows") or 0)
            evidence_refs = int(artifact.get("evidence_ref_count") or 0)
            if selected_rows or bound_rows or evidence_refs:
                if logical_path:
                    entities_selected_by_artifact[logical_path] = max(
                        entities_selected_by_artifact.get(logical_path, 0),
                        bound_rows or selected_rows,
                    )
                evidence_total += evidence_refs
                if evidence_refs:
                    evidence_by_attribute["evidence_ref"] = evidence_by_attribute.get("evidence_ref", 0) + evidence_refs
            metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
            schema_coverage = artifact.get("schema_coverage") if isinstance(artifact.get("schema_coverage"), dict) else {}
            if not schema_coverage and isinstance(metadata.get("schema_coverage"), dict):
                schema_coverage = metadata.get("schema_coverage") or {}
            metadata_coverage = artifact.get("metadata_coverage_summary") if isinstance(artifact.get("metadata_coverage_summary"), dict) else {}
            if not metadata_coverage:
                metadata_coverage = metadata.get("metadata_coverage_summary") if isinstance(metadata.get("metadata_coverage_summary"), dict) else {}
            if not metadata_coverage and isinstance(schema_coverage.get("metadata_coverage_summary"), dict):
                metadata_coverage = schema_coverage.get("metadata_coverage_summary") or {}
            if metadata_coverage:
                metadata_coverage_summaries.append(metadata_coverage)
            inventory_sufficiency = artifact.get("inventory_sufficiency_summary") if isinstance(artifact.get("inventory_sufficiency_summary"), dict) else {}
            if not inventory_sufficiency:
                inventory_sufficiency = metadata.get("inventory_sufficiency_summary") if isinstance(metadata.get("inventory_sufficiency_summary"), dict) else {}
            if not inventory_sufficiency and isinstance(schema_coverage.get("inventory_sufficiency_summary"), dict):
                inventory_sufficiency = schema_coverage.get("inventory_sufficiency_summary") or {}
            if inventory_sufficiency:
                inventory_sufficiency_summaries.append(inventory_sufficiency)
            row_validation = artifact.get("row_validation_summary") if isinstance(artifact.get("row_validation_summary"), dict) else {}
            if not row_validation and isinstance(metadata.get("row_validation_summary"), dict):
                row_validation = metadata.get("row_validation_summary") or {}
            row_evidence = artifact.get("row_evidence_coverage") if isinstance(artifact.get("row_evidence_coverage"), dict) else {}
            if not row_evidence and isinstance(metadata.get("row_evidence_coverage"), dict):
                row_evidence = metadata.get("row_evidence_coverage") or {}
            if row_validation:
                value_counts = row_validation.get("value_counts_by_column") if isinstance(row_validation.get("value_counts_by_column"), dict) else {}
                for key, count in value_counts.items():
                    attribute = str(key)
                    if not attribute:
                        continue
                    evidence_by_attribute[attribute] = max(evidence_by_attribute.get(attribute, 0), int(count or 0))
                coverage_count = int(row_evidence.get("evidence_ref_count") or 0)
                if coverage_count:
                    evidence_total = max(evidence_total, coverage_count)
                    evidence_by_attribute["evidence_ref"] = max(evidence_by_attribute.get("evidence_ref", 0), coverage_count)
                if int(row_validation.get("row_count") or 0) > 0:
                    goals_total = max(goals_total, 1)
                    goals_ready = max(goals_ready, 1)
            artifact_reason = str(artifact.get("reason_code") or "")
            if artifact_reason:
                semantic_gaps.append(
                    {
                        "gap_type": "artifact_projection_reason",
                        "reason_code": artifact_reason,
                        "perception_domain": "artifact_endpoint_projection",
                    }
                )
            provenance = artifact.get("provenance") if isinstance(artifact.get("provenance"), dict) else {}
            contract = metadata.get("declared_contract") if isinstance(metadata.get("declared_contract"), dict) else provenance.get("declared_contract")
            if not isinstance(contract, dict):
                continue
            binding = contract.get("artifact_observation_binding") if isinstance(contract.get("artifact_observation_binding"), dict) else {}
            for key, count in dict(binding.get("bound_counts_by_canonical_key") or {}).items():
                attribute = str(key)
                evidence_by_attribute[attribute] = evidence_by_attribute.get(attribute, 0) + int(count or 0)
                evidence_total += int(count or 0)
            perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
            media = perception.get("media_metadata_capability") if isinstance(perception.get("media_metadata_capability"), dict) else contract.get("media_metadata_capability")
            if isinstance(media, dict) and media:
                media_metadata_summaries.append(media)
            relationship_summary = perception.get("relationship_summary") if isinstance(perception.get("relationship_summary"), dict) else {}
            if relationship_summary:
                relationship_summaries.append(relationship_summary)
            relationship_binding = contract.get("artifact_relationship_binding") if isinstance(contract.get("artifact_relationship_binding"), dict) else {}
            if relationship_binding:
                relationship_bindings.append(relationship_binding)
            relationship_rendering = perception.get("relationship_rendering") if isinstance(perception.get("relationship_rendering"), dict) else {}
            if relationship_rendering:
                relationship_renderings.append(relationship_rendering)
            entity_summary = contract.get("observed_entity_summary") if isinstance(contract.get("observed_entity_summary"), dict) else {}
            for role, paths in dict(entity_summary.get("roots_scanned_by_role") or {}).items():
                current = roots_scanned_by_role.setdefault(str(role), [])
                current.extend(str(item) for item in paths if item and str(item) not in current)
            for role, count in dict(entity_summary.get("entities_by_root_role") or {}).items():
                entities_by_root_role[str(role)] = entities_by_root_role.get(str(role), 0) + int(count or 0)
            for artifact_path, count in dict(entity_summary.get("entities_selected_by_artifact") or {}).items():
                entities_selected_by_artifact[str(artifact_path)] = entities_selected_by_artifact.get(str(artifact_path), 0) + int(count or 0)
            rejected_rows = entity_summary.get("entities_rejected_by_policy") if isinstance(entity_summary.get("entities_rejected_by_policy"), list) else []
            entities_rejected_by_policy += len(rejected_rows)
            workspace_role_mismatches += len(entity_summary.get("workspace_role_mismatches") if isinstance(entity_summary.get("workspace_role_mismatches"), list) else [])
            report = perception.get("semantic_coverage_report") if isinstance(perception.get("semantic_coverage_report"), dict) else contract.get("semantic_coverage_report")
            if isinstance(report, dict) and report:
                reports.append(report)
            coverage2 = perception.get("semantic_coverage_2") if isinstance(perception.get("semantic_coverage_2"), dict) else {}
            if coverage2:
                coverage2_reports.append(coverage2)
            gaps = contract.get("runtime_semantic_gaps") if isinstance(contract.get("runtime_semantic_gaps"), list) else []
            semantic_gaps.extend(item for item in gaps if isinstance(item, dict))
            knowledge_records = perception.get("knowledge_records") if isinstance(perception.get("knowledge_records"), list) else []
            knowledge_record_count += len([item for item in knowledge_records if isinstance(item, dict)])
            assertions = perception.get("semantic_assertions") if isinstance(perception.get("semantic_assertions"), list) else []
            assertion_count += len([item for item in assertions if isinstance(item, dict)])
            truth_eligible_assertion_count += len([
                item for item in assertions if isinstance(item, dict) and bool(item.get("truth_eligible"))
            ])
            self_review = perception.get("semantic_self_review") if isinstance(perception.get("semantic_self_review"), dict) else {}
            if self_review:
                self_review_summaries.append(self_review)
            observation_summary = perception.get("observation_summary") if isinstance(perception.get("observation_summary"), dict) else {}
            if observation_summary:
                goals_ready += len(observation_summary.get("observed_canonical_keys") or [])
            observation_plan = perception.get("observation_plan") if isinstance(perception.get("observation_plan"), dict) else {}
            goals = observation_plan.get("observation_goals") if isinstance(observation_plan.get("observation_goals"), list) else []
            decisions = observation_plan.get("capability_decisions") if isinstance(observation_plan.get("capability_decisions"), list) else []
            goals_total += len(goals)
            goals_blocked += len([
                item for item in decisions if isinstance(item, dict) and str(item.get("decision_status") or "").startswith("BLOCKED")
            ])
            goals_ready += len([
                item for item in decisions if isinstance(item, dict) and item.get("decision_status") == "SELECTED"
            ])
        missing_attributes = sorted({
            str(item)
            for report in reports
            for item in report.get("missing_attributes", [])
            if str(item)
        })
        missing_capabilities = sorted({
            str(item)
            for report in reports
            for item in report.get("missing_capabilities", [])
            if str(item)
        })
        blocking_reasons = sorted({
            str(item)
            for report in reports
            for item in report.get("blocking_reasons", [])
            if str(item)
        } | {
            str(item.get("reason_code"))
            for item in semantic_gaps
            if isinstance(item, dict) and item.get("reason_code")
        } | {
            str(item.get("reason_code"))
            for item in inventory_sufficiency_summaries
            if item.get("reason_code")
        } | {
            str(code)
            for item in metadata_coverage_summaries
            for code in item.get("reason_codes", []) or []
            if str(code)
        })
        latest = reports[-1] if reports else {}
        latest_coverage2 = coverage2_reports[-1] if coverage2_reports else {}
        latest_review = self_review_summaries[-1] if self_review_summaries else {}
        latest_metadata_coverage = metadata_coverage_summaries[-1] if metadata_coverage_summaries else {}
        latest_inventory_sufficiency = inventory_sufficiency_summaries[-1] if inventory_sufficiency_summaries else {}
        return {
            "status": "blocked" if blocked and blocking_reasons else "available" if reports or evidence_total else "not_available",
            "blocking_reason": blocking_reasons[0] if blocking_reasons else None,
            "semantic_coverage": {
                "structural": latest.get("structural_coverage"),
                "entity": latest.get("entity_coverage"),
                "attribute": latest.get("attribute_coverage"),
                "capability": latest.get("capability_coverage"),
                "evidence": latest.get("evidence_coverage"),
                "knowledge": latest_coverage2.get("knowledge_coverage"),
                "truth": latest_coverage2.get("truth_coverage"),
                "semantic": latest_coverage2.get("semantic_coverage"),
            },
            "missing_capabilities": missing_capabilities,
            "missing_attributes": missing_attributes,
            "knowledge": {
                "records": knowledge_record_count,
                "assertions": assertion_count,
                "truth_eligible_assertions": truth_eligible_assertion_count,
                "self_review_truth_readiness": latest_review.get("truth_readiness"),
                "self_review_can_speaker_claim": latest_review.get("can_speaker_claim"),
                "self_review_reason_codes": latest_review.get("reason_codes") or [],
            },
            "observation_goals": {
                "total": goals_total,
                "blocked": goals_blocked,
                "ready": goals_ready,
            },
            "roots_scanned_by_role": roots_scanned_by_role,
            "entities_by_root_role": entities_by_root_role,
            "entities_selected_by_artifact": entities_selected_by_artifact,
            "entities_rejected_by_policy": entities_rejected_by_policy,
            "workspace_role_mismatches": workspace_role_mismatches,
            "media_metadata_capability": self._media_metadata_capability_summary(
                media_metadata_summaries,
                evidence_by_attribute=evidence_by_attribute,
            ),
            "metadata_coverage": latest_metadata_coverage,
            "inventory_sufficiency": latest_inventory_sufficiency,
            "use_safety": latest_inventory_sufficiency.get("use_safety") if isinstance(latest_inventory_sufficiency.get("use_safety"), dict) else {},
            "relationship_cognition": self._relationship_cognition_summary(
                relationship_summaries,
                relationship_bindings,
                relationship_renderings,
            ),
            "evidence": {
                "total_bound_observations": evidence_total,
                "by_attribute": evidence_by_attribute,
                "source": "artifact_observation_binding",
            },
            "reason_codes": blocking_reasons,
            "semantic_gap_count": len(semantic_gaps),
            "source": "artifact_observation_binding",
        }

    def _observational_cognition_summary(self, session: UniversalTaskSession) -> dict[str, Any]:
        reports: list[dict[str, Any]] = []
        semantic_gaps: list[dict[str, Any]] = []
        roots_scanned_by_role: dict[str, list[str]] = {}
        entities_by_root_role: dict[str, int] = {}
        entities_selected_by_artifact: dict[str, int] = {}
        entities_rejected_by_policy = 0
        workspace_role_mismatches = 0
        goals_total = goals_blocked = goals_ready = 0
        knowledge_record_count = 0
        assertion_count = 0
        truth_eligible_assertion_count = 0
        self_review_summaries: list[dict[str, Any]] = []
        coverage2_reports: list[dict[str, Any]] = []
        media_metadata_summaries: list[dict[str, Any]] = []
        relationship_summaries: list[dict[str, Any]] = []
        relationship_bindings: list[dict[str, Any]] = []
        relationship_renderings: list[dict[str, Any]] = []
        metadata_coverage_summaries: list[dict[str, Any]] = []
        inventory_sufficiency_summaries: list[dict[str, Any]] = []
        evidence_total = 0
        evidence_by_attribute: dict[str, int] = {}
        for artifact in session.artifact_state.artifacts:
            metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
            schema_coverage = artifact.get("schema_coverage") if isinstance(artifact.get("schema_coverage"), dict) else {}
            if not schema_coverage and isinstance(metadata.get("schema_coverage"), dict):
                schema_coverage = metadata.get("schema_coverage") or {}
            metadata_coverage = artifact.get("metadata_coverage_summary") if isinstance(artifact.get("metadata_coverage_summary"), dict) else {}
            if not metadata_coverage:
                metadata_coverage = metadata.get("metadata_coverage_summary") if isinstance(metadata.get("metadata_coverage_summary"), dict) else {}
            if not metadata_coverage and isinstance(schema_coverage.get("metadata_coverage_summary"), dict):
                metadata_coverage = schema_coverage.get("metadata_coverage_summary") or {}
            if metadata_coverage:
                metadata_coverage_summaries.append(metadata_coverage)
            inventory_sufficiency = artifact.get("inventory_sufficiency_summary") if isinstance(artifact.get("inventory_sufficiency_summary"), dict) else {}
            if not inventory_sufficiency:
                inventory_sufficiency = metadata.get("inventory_sufficiency_summary") if isinstance(metadata.get("inventory_sufficiency_summary"), dict) else {}
            if not inventory_sufficiency and isinstance(schema_coverage.get("inventory_sufficiency_summary"), dict):
                inventory_sufficiency = schema_coverage.get("inventory_sufficiency_summary") or {}
            if inventory_sufficiency:
                inventory_sufficiency_summaries.append(inventory_sufficiency)
            provenance = artifact.get("provenance") if isinstance(artifact.get("provenance"), dict) else {}
            contract = metadata.get("declared_contract") if isinstance(metadata.get("declared_contract"), dict) else provenance.get("declared_contract")
            if not isinstance(contract, dict):
                continue
            binding = contract.get("artifact_observation_binding") if isinstance(contract.get("artifact_observation_binding"), dict) else {}
            for key, count in dict(binding.get("bound_counts_by_canonical_key") or {}).items():
                attribute = str(key)
                evidence_by_attribute[attribute] = evidence_by_attribute.get(attribute, 0) + int(count or 0)
                evidence_total += int(count or 0)
            perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
            for source in (perception, contract):
                capability_summary = source.get("media_metadata_capability") if isinstance(source.get("media_metadata_capability"), dict) else None
                if capability_summary:
                    media_metadata_summaries.append(capability_summary)
            relationship_summary = perception.get("relationship_summary") if isinstance(perception.get("relationship_summary"), dict) else {}
            if relationship_summary:
                relationship_summaries.append(relationship_summary)
            relationship_binding = contract.get("artifact_relationship_binding") if isinstance(contract.get("artifact_relationship_binding"), dict) else {}
            if relationship_binding:
                relationship_bindings.append(relationship_binding)
            relationship_rendering = perception.get("relationship_rendering") if isinstance(perception.get("relationship_rendering"), dict) else {}
            if relationship_rendering:
                relationship_renderings.append(relationship_rendering)
            entity_summary = contract.get("observed_entity_summary") if isinstance(contract.get("observed_entity_summary"), dict) else {}
            for role, paths in dict(entity_summary.get("roots_scanned_by_role") or {}).items():
                current = roots_scanned_by_role.setdefault(str(role), [])
                current.extend(str(item) for item in paths if item and str(item) not in current)
            for role, count in dict(entity_summary.get("entities_by_root_role") or {}).items():
                entities_by_root_role[str(role)] = entities_by_root_role.get(str(role), 0) + int(count or 0)
            for artifact_path, count in dict(entity_summary.get("entities_selected_by_artifact") or {}).items():
                entities_selected_by_artifact[str(artifact_path)] = entities_selected_by_artifact.get(str(artifact_path), 0) + int(count or 0)
            rejected_rows = entity_summary.get("entities_rejected_by_policy") if isinstance(entity_summary.get("entities_rejected_by_policy"), list) else []
            entities_rejected_by_policy += len(rejected_rows)
            workspace_role_mismatches += len(entity_summary.get("workspace_role_mismatches") if isinstance(entity_summary.get("workspace_role_mismatches"), list) else [])
            report = perception.get("semantic_coverage_report") if isinstance(perception.get("semantic_coverage_report"), dict) else contract.get("semantic_coverage_report")
            if isinstance(report, dict) and report:
                reports.append(report)
            coverage2 = perception.get("semantic_coverage_2") if isinstance(perception.get("semantic_coverage_2"), dict) else {}
            if coverage2:
                coverage2_reports.append(coverage2)
            knowledge_records = perception.get("knowledge_records") if isinstance(perception.get("knowledge_records"), list) else []
            knowledge_record_count += len([item for item in knowledge_records if isinstance(item, dict)])
            assertions = perception.get("semantic_assertions") if isinstance(perception.get("semantic_assertions"), list) else []
            assertion_count += len([item for item in assertions if isinstance(item, dict)])
            truth_eligible_assertion_count += len([
                item for item in assertions if isinstance(item, dict) and bool(item.get("truth_eligible"))
            ])
            self_review = perception.get("semantic_self_review") if isinstance(perception.get("semantic_self_review"), dict) else {}
            if self_review:
                self_review_summaries.append(self_review)
            observation_plan = perception.get("observation_plan") if isinstance(perception.get("observation_plan"), dict) else {}
            goals = observation_plan.get("observation_goals") if isinstance(observation_plan.get("observation_goals"), list) else []
            decisions = observation_plan.get("capability_decisions") if isinstance(observation_plan.get("capability_decisions"), list) else []
            goals_total += len(goals)
            goals_blocked += len([item for item in decisions if isinstance(item, dict) and str(item.get("decision_status") or "").startswith("BLOCKED")])
            goals_ready += len([item for item in decisions if isinstance(item, dict) and item.get("decision_status") == "SELECTED"])
            gaps = contract.get("runtime_semantic_gaps") if isinstance(contract.get("runtime_semantic_gaps"), list) else []
            semantic_gaps.extend(item for item in gaps if isinstance(item, dict))
        missing_attributes = sorted({
            str(item)
            for report in reports
            for item in report.get("missing_attributes", [])
            if str(item)
        })
        missing_capabilities = sorted({
            str(item)
            for report in reports
            for item in report.get("missing_capabilities", [])
            if str(item)
        })
        blocking_reasons = sorted({
            str(item)
            for report in reports
            for item in report.get("blocking_reasons", [])
            if str(item)
        } | {
            str(item.get("reason_code"))
            for item in semantic_gaps
            if isinstance(item, dict) and item.get("reason_code")
        } | {
            str(item.get("reason_code"))
            for item in inventory_sufficiency_summaries
            if item.get("reason_code")
        } | {
            str(code)
            for item in metadata_coverage_summaries
            for code in item.get("reason_codes", []) or []
            if str(code)
        })
        latest = reports[-1] if reports else {}
        latest_coverage2 = coverage2_reports[-1] if coverage2_reports else {}
        latest_review = self_review_summaries[-1] if self_review_summaries else {}
        latest_metadata_coverage = metadata_coverage_summaries[-1] if metadata_coverage_summaries else {}
        latest_inventory_sufficiency = inventory_sufficiency_summaries[-1] if inventory_sufficiency_summaries else {}
        blocked = session.status == "BLOCKED" or session.validation_state.status == "blocked"
        return {
            "status": "blocked" if blocked and blocking_reasons else "available" if reports else "not_available",
            "blocking_reason": blocking_reasons[0] if blocking_reasons else None,
            "semantic_coverage": {
                "structural": latest.get("structural_coverage"),
                "entity": latest.get("entity_coverage"),
                "attribute": latest.get("attribute_coverage"),
                "capability": latest.get("capability_coverage"),
                "evidence": latest.get("evidence_coverage"),
                "knowledge": latest_coverage2.get("knowledge_coverage"),
                "truth": latest_coverage2.get("truth_coverage"),
                "semantic": latest_coverage2.get("semantic_coverage"),
            },
            "knowledge": {
                "records": knowledge_record_count,
                "assertions": assertion_count,
                "truth_eligible_assertions": truth_eligible_assertion_count,
                "self_review_truth_readiness": latest_review.get("truth_readiness"),
                "self_review_can_speaker_claim": latest_review.get("can_speaker_claim"),
                "self_review_reason_codes": latest_review.get("reason_codes") or [],
            },
            "missing_capabilities": missing_capabilities,
            "missing_attributes": missing_attributes,
            "observation_goals": {
                "total": goals_total,
                "blocked": goals_blocked,
                "ready": goals_ready,
            },
            "roots_scanned_by_role": roots_scanned_by_role,
            "entities_by_root_role": entities_by_root_role,
            "entities_selected_by_artifact": entities_selected_by_artifact,
            "entities_rejected_by_policy": entities_rejected_by_policy,
            "workspace_role_mismatches": workspace_role_mismatches,
            "media_metadata_capability": self._media_metadata_capability_summary(
                media_metadata_summaries,
                evidence_by_attribute=evidence_by_attribute,
            ),
            "metadata_coverage": latest_metadata_coverage,
            "inventory_sufficiency": latest_inventory_sufficiency,
            "use_safety": latest_inventory_sufficiency.get("use_safety") if isinstance(latest_inventory_sufficiency.get("use_safety"), dict) else {},
            "relationship_cognition": self._relationship_cognition_summary(
                relationship_summaries,
                relationship_bindings,
                relationship_renderings,
            ),
            "evidence": {
                "total_bound_observations": evidence_total,
                "by_attribute": evidence_by_attribute,
                "source": "artifact_observation_binding",
            },
            "reason_codes": blocking_reasons,
            "semantic_gap_count": len(semantic_gaps),
            "source": "artifact_declared_contract_perception",
        }

    def _relationship_cognition_summary(
        self,
        summaries: list[dict[str, Any]],
        bindings: list[dict[str, Any]],
        renderings: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        renderings = renderings or []
        candidate_count = sum(int(item.get("candidate_count") or 0) for item in summaries)
        observation_count = sum(int(item.get("observation_count") or 0) for item in summaries)
        evidence_count = sum(int(item.get("evidence_count") or item.get("evidence_signal_count") or 0) for item in summaries)
        provenance_trace_count = sum(int(item.get("provenance_trace_count") or 0) for item in summaries)
        conflict_count = sum(int(item.get("conflict_count") or 0) for item in summaries)
        negative_evidence_count = sum(int(item.get("negative_evidence_count") or 0) for item in summaries)
        families = sorted({
            str(family)
            for item in [*summaries, *bindings]
            for family in item.get("relation_families", []) or []
            if str(family)
        })
        reason_codes = sorted({
            str(code)
            for item in summaries
            for code in item.get("reason_codes", []) or []
            if str(code)
        })
        confidence_values: list[float] = []
        for item in [*summaries, *bindings]:
            confidence = item.get("confidence_summary") or item.get("relationship_confidence_summary")
            if isinstance(confidence, dict) and confidence.get("max") is not None:
                confidence_values.append(float(confidence.get("max") or 0.0))
        if bindings and not observation_count:
            observation_count = sum(int(item.get("bound_relationship_observation_count") or 0) for item in bindings)
        if bindings and not candidate_count:
            candidate_count = sum(int(item.get("candidate_count") or 0) for item in bindings)
        if bindings and not evidence_count:
            evidence_count = sum(int(item.get("evidence_signal_count") or 0) for item in bindings)
        if bindings and not provenance_trace_count:
            provenance_trace_count = sum(len(item.get("relationship_provenance_traces") or []) for item in bindings)
        if bindings and not conflict_count:
            conflict_count = sum(
                len(observation.get("conflicts") or [])
                for binding in bindings
                for observation in binding.get("bound_relationship_observations", []) or []
                if isinstance(observation, dict)
            )
        if bindings and not negative_evidence_count:
            negative_evidence_count = sum(
                len(observation.get("negative_evidence") or [])
                for binding in bindings
                for observation in binding.get("bound_relationship_observations", []) or []
                if isinstance(observation, dict)
            )
        status = "available" if observation_count > 0 else "blocked" if reason_codes else "not_available"
        if status == "not_available":
            reason_codes = ["RELATIONSHIP_OBSERVATION_NOT_BOUND"]
        rendered_field_count = sum(int(item.get("rendered_field_count") or 0) for item in renderings)
        evidence_ref_count = sum(int(item.get("evidence_ref_count") or 0) for item in renderings)
        provenance_ref_count = sum(int(item.get("provenance_ref_count") or 0) for item in renderings)
        validation_ready_count = sum(int(item.get("validation_ready_count") or 0) for item in renderings)
        conflicted_relationship_count = sum(int(item.get("conflicted_relationship_count") or 0) for item in renderings)
        validated_relationship_count = sum(int(item.get("validated_relationship_count") or 0) for item in renderings)
        validation_status = next((str(item.get("validation_status")) for item in reversed(renderings) if item.get("validation_status")), "validation_required" if observation_count else "blocked")
        return {
            "status": status,
            "candidate_count": candidate_count,
            "observation_count": observation_count,
            "evidence_count": evidence_count,
            "provenance_trace_count": provenance_trace_count,
            "conflict_count": conflict_count,
            "negative_evidence_count": negative_evidence_count,
            "rendered_field_count": rendered_field_count,
            "evidence_ref_count": evidence_ref_count,
            "provenance_ref_count": provenance_ref_count,
            "validation_ready_count": validation_ready_count,
            "validated_relationship_count": validated_relationship_count,
            "conflicted_relationship_count": conflicted_relationship_count,
            "relation_families": families,
            "confidence_summary": {
                "count": len(confidence_values),
                "max": round(max(confidence_values), 4) if confidence_values else 0.0,
                "average": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
            },
            "truth_eligible": False,
            "validation_status": validation_status,
            "reason_codes": reason_codes,
            "source": "artifact_relationship_binding",
        }

    def _media_metadata_capability_summary(
        self,
        summaries: list[dict[str, Any]],
        *,
        evidence_by_attribute: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        media_attributes = {
            "codec",
            "container",
            "bitrate",
            "bitrate_bps",
            "sample_rate",
            "sample_rate_hz",
            "channels",
            "duration",
            "duration_ms",
            "artwork",
            "artwork_present",
            "metadata",
        }
        observed_media_attributes = sorted(
            key
            for key, count in dict(evidence_by_attribute or {}).items()
            if key in media_attributes and int(count or 0) > 0
        )
        if not summaries:
            if observed_media_attributes:
                return {
                    "status": "unknown_due_to_payload_ref",
                    "capability_id": "media_metadata_reader",
                    "primary_backend": "mutagen",
                    "selected_backend": None,
                    "available_backends": [],
                    "blocked_backends": [],
                    "globally_blocked_backends": [],
                    "partially_blocked_backends": [],
                    "missing_dependency": [],
                    "attempted_backends": [],
                    "successful_backends": [],
                    "fallback_backends_used": [],
                    "backend_error_counts": {},
                    "evidence_records_created": 0,
                    "attributes_observed": observed_media_attributes,
                    "attributes_missing": [],
                    "limitations": ["capability_provenance_not_inline_in_summary"],
                    "source": "artifact_observation_binding",
                }
            return {
                "status": "not_configured",
                "capability_id": "media_metadata_reader",
                "primary_backend": "mutagen",
                "selected_backend": None,
                "available_backends": [],
                "blocked_backends": [],
                "globally_blocked_backends": [],
                "partially_blocked_backends": [],
                "missing_dependency": [],
                "attempted_backends": [],
                "successful_backends": [],
                "fallback_backends_used": [],
                "backend_error_counts": {},
                "evidence_records_created": 0,
                "attributes_observed": [],
                "attributes_missing": [],
                "limitations": [],
            }
        latest = summaries[-1]
        backend_attempt_counts: dict[str, int] = {}
        backend_success_counts: dict[str, int] = {}
        backend_block_counts: dict[str, int] = {}
        backend_error_counts: dict[str, int] = {}
        for summary in summaries:
            for backend in summary.get("attempted_backends", []) or []:
                key = str(backend)
                backend_attempt_counts[key] = backend_attempt_counts.get(key, 0) + 1
            for backend in summary.get("successful_backends", []) or []:
                key = str(backend)
                backend_success_counts[key] = backend_success_counts.get(key, 0) + 1
            for backend in summary.get("blocked_backends", []) or []:
                key = str(backend)
                backend_block_counts[key] = backend_block_counts.get(key, 0) + 1
            for code, count in dict(summary.get("backend_error_counts") or {}).items():
                key = str(code)
                backend_error_counts[key] = backend_error_counts.get(key, 0) + int(count or 0)
        return {
            "status": latest.get("status") or "partial",
            "capability_id": latest.get("capability_id") or "media_metadata_reader",
            "primary_backend": latest.get("primary_backend") or "mutagen",
            "selected_backend": latest.get("selected_backend"),
            "available_backends": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("available_backends", [])
                if item
            }),
            "blocked_backends": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("blocked_backends", [])
                if item
            }),
            "globally_blocked_backends": sorted(
                backend
                for backend, count in backend_attempt_counts.items()
                if count > 0 and backend_success_counts.get(backend, 0) == 0 and backend_block_counts.get(backend, 0) >= count
            ),
            "partially_blocked_backends": sorted(
                backend
                for backend, count in backend_block_counts.items()
                if count > 0 and backend_success_counts.get(backend, 0) > 0
            ),
            "missing_dependency": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("missing_dependency", [])
                if item
            }),
            "attempted_backends": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("attempted_backends", [])
                if item
            }),
            "successful_backends": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("successful_backends", [])
                if item
            }),
            "fallback_backends_used": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("fallback_backends_used", [])
                if item
            }),
            "backend_error_counts": backend_error_counts,
            "evidence_records_created": sum(int(summary.get("evidence_records_created") or 0) for summary in summaries),
            "attributes_observed": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("attributes_observed", [])
                if item
            }),
            "attributes_missing": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("attributes_missing", [])
                if item
            }),
            "limitations": sorted({
                str(item)
                for summary in summaries
                for item in summary.get("limitations", [])
                if item
            }),
        }

    def _canonical_runtime_context(
        self,
        *,
        workspace_context: Any,
        retrieval_context: Any,
        execution_context: Any,
    ) -> dict[str, Any]:
        return {
            "workspace": workspace_context.model_dump(mode="json") if workspace_context is not None else None,
            "retrieval": retrieval_context.model_dump(mode="json") if retrieval_context is not None else None,
            "execution": execution_context.model_dump(mode="json") if execution_context is not None else None,
            "source": "universal_task_session_service",
        }
