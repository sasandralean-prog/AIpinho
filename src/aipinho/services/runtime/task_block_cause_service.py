from __future__ import annotations

from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_block_cause import TaskBlockCause
from aipinho.services.regression.operational_trust_candidate_service import OperationalTrustCandidateService
from aipinho.utils.yaml_loader import load_yaml_file


class TaskBlockCauseService:
    def __init__(self, config_path=None, regression_candidates=None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "task_block_explainability.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=PATHS.config_root / "runtime")
        self.regression_candidates = regression_candidates or OperationalTrustCandidateService()

    def build(
        self,
        run,
        reasons: list[str],
        *,
        operation_id: str | None = None,
        operation_type: str | None = None,
        blocked_stage: str | None = None,
        event_id: str | None = None,
        validation: dict[str, Any] | None = None,
    ) -> TaskBlockCause:
        reason = next((str(item) for item in reasons if str(item).strip()), "unknown_block_reason")
        configured = self.config.get("reasons", {}).get(reason, {})
        defaults = self.config.get("defaults", {})
        stage = str(blocked_stage or configured.get("blocked_stage") or defaults.get("blocked_stage") or "unknown")
        intent = run.intent_map if isinstance(getattr(run, "intent_map", None), dict) else {}
        cause = TaskBlockCause(
            block_id=f"task_block_{uuid4().hex}",
            task_id=getattr(run, "task_id", None) or run.run_id,
            operation_id=operation_id or intent.get("operation_id"),
            operation_type=operation_type or intent.get("operation_type") or intent.get("overall_intent") or run.contract_type,
            blocked_stage=stage,
            block_reason_code=reason,
            human_reason=str(configured.get("human_reason") or defaults.get("human_reason")),
            technical_reason_sanitized="; ".join(dict.fromkeys(str(item) for item in reasons))[:1000],
            policy_name=str(run.policy_snapshot.get("policy_name") or "task_runtime_policy"),
            policy_decision_id=run.policy_snapshot.get("decision_id"),
            capability_requested=self._capability(run),
            workspace_id=run.workspace,
            workspace_role="source_readonly" if run.mode == "read_only" else None,
            source_read_status="blocked" if stage in {"source_read_policy", "workspace_resolution"} else "not_started",
            artifact_output_status="not_created",
            approval_status=self._approval_status(run, stage),
            validation_status=str((validation or {}).get("status") or "not_started"),
            validation_id=(validation or {}).get("validation_id"),
            failure_summary=(validation or {}).get("failure_summary"),
            failed_checks=list((validation or {}).get("failed_checks") or []),
            safe_alternatives=list(configured.get("safe_alternatives") or defaults.get("safe_alternatives") or []),
            evidence_refs=[{"type": "task_run", "ref_id": run.run_id}, {"type": "task_trace", "ref_id": f"task-runs/{run.run_id}/trace"}],
            trace_id=f"task-runs/{run.run_id}/trace",
            event_id=event_id,
        )
        if stage == "unknown":
            self._record_unknown(cause)
        return cause

    @staticmethod
    def _capability(run) -> str | None:
        actions = list(getattr(run, "requested_actions", []) or [])
        if any(item in {"read_files", "list_files", "inspect_workspace"} for item in actions):
            return "read_workspace"
        return actions[0] if actions else None

    @staticmethod
    def _approval_status(run, stage: str) -> str:
        if stage == "approval_required":
            return "pending"
        if stage == "approval_denied":
            return "denied"
        return "not_required"

    def _record_unknown(self, cause: TaskBlockCause) -> None:
        try:
            self.regression_candidates.create_for_failure(
                category="event_contract_missing",
                source="task_block_cause_service",
                expected_behavior={"blocked_stage": "known", "structured_reason": True},
                observed_behavior={"block_reason_code": cause.block_reason_code, "blocked_stage": cause.blocked_stage},
            )
        except Exception:
            pass
