from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.canonical_operation_state import CanonicalOperationState, CanonicalOperationStatus
from aipinho.schemas.runtime.runtime_truth import RuntimeTruth
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_result import TaskRunResult


_TERMINAL_BLOCKED = {"blocked", "failed", "cancelled", "expired"}
_BAD_VALIDATION = {"blocked", "failed", "rejected", "needs_review", "degraded", "incomplete", "missing"}


class CanonicalOperationStateService:
    """Derives one authoritative state for lifecycle, completion, truth and UI."""

    def derive(
        self,
        run: TaskRun,
        *,
        result: TaskRunResult | None = None,
        truth: RuntimeTruth | None = None,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> CanonicalOperationState:
        artifact_rows = artifacts if artifacts is not None else list(run.produced_artifacts)
        missing_artifacts = self._missing_artifacts(run, artifact_rows)
        completion = result.completion if result else None
        missing_outputs = list(getattr(completion, "missing_outcomes", []) or [])
        validation_status = self._validation_status(result)
        lifecycle_status = str(run.status or "")
        completion_status = str(getattr(completion, "status", "") or (result.status if result else ""))
        reason = self._reason_code(run, result, truth)
        status = self._status(
            lifecycle_status=lifecycle_status,
            completion_status=completion_status,
            validation_status=validation_status,
            missing_outputs=missing_outputs,
            missing_artifacts=missing_artifacts,
            result=result,
            truth=truth,
        )
        safe = bool(
            status == "COMPLETED"
            and truth is not None
            and truth.safe_to_report_success
            and not missing_outputs
            and not missing_artifacts
            and validation_status not in _BAD_VALIDATION
        )
        return CanonicalOperationState(
            status=status,
            task_id=run.task_id or run.run_id,
            task_run_id=run.run_id,
            operation_id=run.operation_id,
            lifecycle_status=lifecycle_status,
            validation_status=validation_status,
            completion_status=completion_status or None,
            speaker_truth_status=truth.speaker_truth_status if truth else None,
            ui_status=self._ui_status(status),
            safe_to_report_success=safe,
            missing_outputs=missing_outputs,
            missing_artifacts=missing_artifacts,
            reason_code=reason,
            evidence_refs=self._evidence_refs(run, truth, artifact_rows),
            metadata={
                "produced_artifacts": [item.get("artifact_id") for item in artifact_rows if item.get("artifact_id")],
                "required_artifacts": list(run.required_artifacts),
                "contract_type": run.contract_type,
                "operation_type": run.operation_type,
                "runtime_profile": run.runtime_profile,
            },
        )

    def bind_artifacts(self, run: TaskRun, artifacts: list[dict[str, Any]], *, required: list[str] | None = None) -> TaskRun:
        required_artifacts = list(dict.fromkeys(required or run.required_artifacts))
        normalized = [self._normalize_artifact(run, item) for item in artifacts]
        run.required_artifacts = required_artifacts
        run.produced_artifacts = normalized
        run.missing_artifacts = self._missing_artifacts(run, normalized)
        if run.execution_context is not None:
            run.execution_context.artifacts = normalized
        return run

    def _status(
        self,
        *,
        lifecycle_status: str,
        completion_status: str,
        validation_status: str | None,
        missing_outputs: list[str],
        missing_artifacts: list[str],
        result: TaskRunResult | None,
        truth: RuntimeTruth | None,
    ) -> CanonicalOperationStatus:
        if lifecycle_status == "cancelled" or (result and result.status == "cancelled"):
            return "CANCELLED"
        if lifecycle_status in {"failed", "expired"}:
            return "FAILED"
        if missing_artifacts:
            return "WAITING_ARTIFACTS" if result is None else "BLOCKED"
        if missing_outputs:
            return "BLOCKED"
        if validation_status in _BAD_VALIDATION:
            return "BLOCKED"
        if completion_status in {"blocked", "failed"} or lifecycle_status == "blocked":
            return "BLOCKED"
        if truth and truth.status in {"blocked", "failed"}:
            return "BLOCKED"
        if completion_status == "completed" and truth and truth.safe_to_report_success:
            return "COMPLETED"
        if result and result.status == "completed" and truth is None:
            return "BLOCKED"
        if result and result.status == "completed" and truth and truth.status == "completed" and not truth.safe_to_report_success:
            return "BLOCKED"
        if lifecycle_status == "waiting_input":
            return "WAITING_APPROVAL"
        if lifecycle_status in {"created", "queued"}:
            return "READY" if lifecycle_status == "queued" else "CREATED"
        if lifecycle_status in {"running", "waiting_delegation"}:
            return "RUNNING"
        return "CREATED"

    def _validation_status(self, result: TaskRunResult | None) -> str | None:
        if result is None:
            return "not_started"
        if isinstance(result.validation, dict):
            return str(result.validation.get("status") or result.validation.get("validation_status") or "")
        return None

    def _missing_artifacts(self, run: TaskRun, artifacts: list[dict[str, Any]]) -> list[str]:
        if not run.required_artifacts:
            return []
        produced = {
            str(value)
            for item in artifacts
            for value in (item.get("logical_path"), item.get("artifact_id"), item.get("storage_ref"))
            if value
        }
        return [item for item in run.required_artifacts if item not in produced]

    def _normalize_artifact(self, run: TaskRun, item: dict[str, Any]) -> dict[str, Any]:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        return {
            **item,
            "task_id": item.get("task_id") or metadata.get("task_id") or run.task_id or run.run_id,
            "task_run_id": item.get("task_run_id") or metadata.get("task_run_id") or run.run_id,
            "operation_id": item.get("operation_id") or run.operation_id,
            "phase_id": item.get("phase_id") or metadata.get("phase_id") or run.current_phase,
            "workspace_id": item.get("workspace_id") or run.workspace_id,
            "logical_path": item.get("logical_path") or metadata.get("logical_path"),
            "storage_ref": item.get("storage_ref") or item.get("storage_path"),
            "producer_step": item.get("producer_step") or metadata.get("producer_step"),
            "created_at": item.get("created_at"),
            "validation_status": item.get("validation_status") or "unknown",
        }

    def _reason_code(self, run: TaskRun, result: TaskRunResult | None, truth: RuntimeTruth | None) -> str | None:
        if truth and truth.reason_code:
            return truth.reason_code
        if result and result.status == "completed" and truth is None:
            return "runtime_truth_required"
        if result and getattr(result, "reason_code", None):
            return str(result.reason_code)
        if result and result.block_cause:
            return result.block_cause.block_reason_code
        if run.block_cause:
            return run.block_cause.block_reason_code
        if run.blocked_reasons:
            return ",".join(run.blocked_reasons)
        return None

    def _evidence_refs(self, run: TaskRun, truth: RuntimeTruth | None, artifacts: list[dict[str, Any]]) -> list[str]:
        refs = [f"task_run:{run.run_id}"]
        if truth:
            refs.append(f"truth:{truth.truth_id}")
        refs.extend(f"artifact:{item.get('artifact_id')}" for item in artifacts if item.get("artifact_id"))
        return list(dict.fromkeys(refs))

    def _ui_status(self, status: CanonicalOperationStatus) -> str:
        return status.lower()
