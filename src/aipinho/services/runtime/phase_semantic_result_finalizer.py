from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.phase_semantic_completion_policy import (
    PhaseCompletionDecision,
    PhaseSemanticCompletionPolicy,
)


class PhaseSemanticResultFinalizer:
    """Build terminal results from governed artifact semantic state.

    This service is intentionally narrow: it consumes already materialized
    artifact summaries and never observes the filesystem or infers metadata.
    """

    source = "phase_semantic_completion_policy"

    def __init__(self, policy: PhaseSemanticCompletionPolicy | None = None) -> None:
        self.policy = policy or PhaseSemanticCompletionPolicy()

    def can_finalize(self, artifacts: list[dict[str, Any]]) -> bool:
        return self._evidence_bound_semantic_artifact(artifacts) is not None

    def build_result(
        self,
        *,
        run: TaskRun,
        artifacts: list[dict[str, Any]],
        artifact_state: dict[str, Any],
        events_count: int,
        finished_at: str | None = None,
    ) -> TaskRunResult | None:
        if not self.can_finalize(artifacts):
            return None
        validation_seed = self._validation_seed(run=run, artifacts=artifacts, artifact_state=artifact_state)
        decision = self.policy.evaluate(
            phase_id=str(run.current_phase or "phase_1"),
            phase_kind="discovery",
            runtime_status=str(run.status or "blocked"),
            validation=validation_seed,
            artifacts=artifacts,
        )
        validation = self._validation_from_decision(decision)
        completion = self._completion_from_decision(decision)
        result_status = self._result_status(decision)
        timestamp = finished_at or run.finished_at or datetime.now(timezone.utc).isoformat()
        return TaskRunResult(
            run_id=run.run_id,
            status=result_status,  # type: ignore[arg-type]
            source=self.source,
            reason_code=None if result_status == "completed" else decision.reason_code,
            finished_at=timestamp,
            summary=self._summary(decision, artifacts),
            outputs={
                "terminal_result_finalization": {
                    "reason_code": decision.reason_code,
                    "source": self.source,
                    "finalized_from_terminal_run": True,
                    "semantic_result_finalization": "completed",
                    "safe_to_report_success": decision.safe_to_report_success,
                    "store_repair_suppressed_due_to_semantic_artifact_state": True,
                },
                "artifact_result": {
                    "artifact_ids": [str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")],
                    "logical_paths": self._logical_paths(artifacts),
                    "artifacts": artifacts,
                    "artifact_state": artifact_state,
                },
                "validation_result": validation,
                "phase_semantic_completion_decision": self._decision_payload(decision),
            },
            warnings=[],
            blocked_items=list(decision.blocking_findings or decision.missing_outputs),
            events_count=events_count,
            trace_ref=f"task-runs/{run.run_id}/trace",
            safe_to_display=True,
            validation={
                "status": validation["status"],
                "score": 1.0 if validation["status"] in {"passed", "passed_with_limitations"} else 0.0,
                "safe_to_display": True,
                "safe_to_report_success": decision.safe_to_report_success,
                "reason_code": decision.reason_code,
                "phase_contract_status": decision.phase_contract_status,
                "artifact_sufficiency_status": decision.artifact_sufficiency_status,
                "safe_for_limited_discovery": decision.safe_for_limited_discovery,
                "blocking_findings": list(decision.blocking_findings),
                "limiting_findings": list(decision.limiting_findings),
            },
            completion=completion,
        )

    def _validation_seed(
        self,
        *,
        run: TaskRun,
        artifacts: list[dict[str, Any]],
        artifact_state: dict[str, Any],
    ) -> dict[str, Any]:
        logical_paths = self._logical_paths(artifacts)
        safe = artifact_state.get("safe_to_use") is True
        reason_code = str(artifact_state.get("reason_code") or self._artifact_reason(artifacts) or "PHASE_REQUIRED_ARTIFACTS_INSUFFICIENT")
        return {
            "status": "passed" if safe else "blocked",
            "reason_code": reason_code,
            "expected_outputs": list(run.required_artifacts or logical_paths),
            "fulfilled_outputs": logical_paths,
            "missing_outputs": [] if safe else [reason_code],
            "safe_to_report_success": safe,
        }

    def _validation_from_decision(self, decision: PhaseCompletionDecision) -> dict[str, Any]:
        return {
            "status": decision.validation_status,
            "reason_code": decision.reason_code,
            "safe_to_report_success": decision.safe_to_report_success,
            "safe_to_continue": decision.safe_to_report_success,
            "phase_contract_status": decision.phase_contract_status,
            "artifact_sufficiency_status": decision.artifact_sufficiency_status,
            "safe_for_limited_discovery": decision.safe_for_limited_discovery,
            "blocking_findings": list(decision.blocking_findings),
            "limiting_findings": list(decision.limiting_findings),
            "limited_outputs": list(decision.limited_outputs),
        }

    def _completion_from_decision(self, decision: PhaseCompletionDecision) -> TaskCompletionEvaluation:
        status = decision.status if decision.status in {"completed", "completed_with_limitations", "partial", "failed", "blocked", "cancelled"} else "blocked"
        return TaskCompletionEvaluation(
            status=status,  # type: ignore[arg-type]
            safe_to_report_success=decision.safe_to_report_success,
            expected_outcomes=list(decision.expected_outputs),
            fulfilled_outcomes=list(decision.fulfilled_outputs),
            missing_outcomes=list(decision.missing_outputs),
            warnings=[],
            limitations=list(decision.limitations),
            metadata={
                "reason_code": decision.reason_code,
                "source": self.source,
                "allowed_claims": list(decision.allowed_claims),
                "forbidden_claims": list(decision.forbidden_claims),
                "required_disclosures": list(decision.required_disclosures),
                "phase_dependency": dict(decision.phase_dependency),
            },
        )

    def _decision_payload(self, decision: PhaseCompletionDecision) -> dict[str, Any]:
        return decision.metadata | {
            "status": decision.status,
            "reason_code": decision.reason_code,
            "source": self.source,
            "safe_to_report_success": decision.safe_to_report_success,
            "phase_contract_status": decision.phase_contract_status,
            "artifact_sufficiency_status": decision.artifact_sufficiency_status,
            "safe_for_limited_discovery": decision.safe_for_limited_discovery,
            "partial_artifact_accepted": decision.partial_artifact_accepted,
            "phase_dependency": decision.phase_dependency,
        }

    def _result_status(self, decision: PhaseCompletionDecision) -> str:
        if decision.status == "completed_with_limitations":
            return "completed_with_limitations"
        if decision.status in {"completed", "partial", "failed", "cancelled", "blocked"}:
            return decision.status
        return "blocked"

    def _summary(self, decision: PhaseCompletionDecision, artifacts: list[dict[str, Any]]) -> str:
        if decision.status == "completed_with_limitations":
            return "Phase completed with governed semantic limitations."
        if decision.status == "completed":
            return "Phase completed with governed semantic artifact evidence."
        return "Phase semantic completion policy blocked terminal success."

    def _logical_paths(self, artifacts: list[dict[str, Any]]) -> list[str]:
        return list(
            dict.fromkeys(
                str(item.get("logical_path") or (item.get("metadata") or {}).get("logical_path") or "")
                for item in artifacts
                if item.get("logical_path") or (isinstance(item.get("metadata"), dict) and (item.get("metadata") or {}).get("logical_path"))
            )
        )

    def _artifact_reason(self, artifacts: list[dict[str, Any]]) -> str | None:
        semantic = self._evidence_bound_semantic_artifact(artifacts)
        if not semantic:
            return None
        metadata = semantic.get("metadata") if isinstance(semantic.get("metadata"), dict) else {}
        reason = semantic.get("reason_code") or metadata.get("reason_code")
        return str(reason) if reason else None

    def _evidence_bound_semantic_artifact(self, artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
        for item in artifacts:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            semantic_status = str(item.get("semantic_contract_status") or metadata.get("semantic_contract_status") or "")
            reason = str(item.get("reason_code") or metadata.get("reason_code") or "")
            bound_rows = self._int(item.get("bound_rows") or metadata.get("bound_rows"))
            evidence_refs = self._int(item.get("evidence_ref_count") or metadata.get("evidence_ref_count"))
            if (semantic_status == "partial" or reason == "MUSIC_INVENTORY_PARTIAL_EVIDENCE") and bound_rows > 0 and evidence_refs > 0:
                return item
        return None

    def _int(self, value: Any) -> int:
        try:
            return int(value or 0)
        except Exception:
            return 0
