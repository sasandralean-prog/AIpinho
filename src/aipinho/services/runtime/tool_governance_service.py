from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.runtime.tool_governance import (
    ToolGovernanceAudit,
    ToolGovernanceCheckpoint,
    ToolGovernanceStage,
    ToolGovernanceTrail,
)


class ToolGovernanceService:
    STAGES: tuple[ToolGovernanceStage, ...] = (
        "intent",
        "planner",
        "contract",
        "capability",
        "policy",
        "approval",
        "tool_router",
        "execution",
        "validation",
        "artifacts",
        "report",
    )

    SIDE_EFFECT_ACTIONS = {
        "run_command",
        "apply_patch",
        "write_file",
        "write_files",
        "create_file",
        "create_directory",
        "modify_file",
        "delete",
        "delete_file",
        "move",
        "move_file",
        "format",
        "install",
        "build",
        "clean",
        "shell_build",
        "shell_test",
    }
    ARTIFACT_ACTIONS = {"artifact", "artifact_create", "artifact_generate", "create_artifact", "generate_report"}

    def build_trail(self, run: TaskRun, result: TaskRunResult | None = None) -> ToolGovernanceTrail:
        checkpoints = [
            self._intent_checkpoint(run),
            self._planner_checkpoint(run),
            self._contract_checkpoint(run),
            self._capability_checkpoint(run),
            self._policy_checkpoint(run),
            self._approval_checkpoint(run),
            self._tool_router_checkpoint(run),
            self._execution_checkpoint(run),
            self._validation_checkpoint(run, result),
            self._artifacts_checkpoint(run, result),
            self._report_checkpoint(run, result),
        ]
        missing = [item.stage for item in checkpoints if item.required and item.status == "missing"]
        blocked = [item.stage for item in checkpoints if item.status == "blocked"]
        traceable = not missing and not blocked
        status = "ready" if traceable else "blocked" if blocked else "incomplete"
        warnings = []
        if self._side_effect_requested(run) and not self._has_execution_plan(run):
            warnings.append("side_effect_action_without_execution_plan")
        if result and result.status == "completed" and not self._result_has_operational_evidence(result):
            warnings.append("completed_result_without_operational_evidence")
        return ToolGovernanceTrail(
            run_id=run.run_id,
            status=status,
            action=self._primary_action(run),
            contract_type=run.contract_type,
            operation_type=run.operation_type,
            runtime_profile=run.runtime_profile,
            checkpoints=checkpoints,
            missing_required_stages=missing,
            blocked_stages=blocked,
            traceable=traceable,
            warnings=warnings,
        )

    def audit(self, trail: ToolGovernanceTrail) -> ToolGovernanceAudit:
        if trail.traceable:
            return ToolGovernanceAudit(
                trail_id=trail.trail_id,
                run_id=trail.run_id,
                status="passed",
                reason="tool_governance_trail_traceable",
                missing_required_stages=[],
                blocked_stages=[],
                traceable=True,
            )
        reason = "tool_governance_blocked" if trail.blocked_stages else "tool_governance_incomplete"
        return ToolGovernanceAudit(
            trail_id=trail.trail_id,
            run_id=trail.run_id,
            status="failed",
            reason=reason,
            missing_required_stages=trail.missing_required_stages,
            blocked_stages=trail.blocked_stages,
            traceable=False,
        )

    def build_and_audit(self, run: TaskRun, result: TaskRunResult | None = None) -> tuple[ToolGovernanceTrail, ToolGovernanceAudit]:
        trail = self.build_trail(run, result=result)
        return trail, self.audit(trail)

    def _intent_checkpoint(self, run: TaskRun) -> ToolGovernanceCheckpoint:
        intent = run.intent_map if isinstance(run.intent_map, dict) else {}
        present = bool(intent.get("intent_type") or intent.get("operation_type") or run.operation_type or run.contract_type)
        return self._checkpoint(
            "intent",
            "present" if present else "missing",
            "Intent map or operation type is available." if present else "Intent evidence is missing.",
            evidence_refs=[{"kind": "intent_map", "value": self._sanitize_small(intent)}] if present else [],
        )

    def _planner_checkpoint(self, run: TaskRun) -> ToolGovernanceCheckpoint:
        plan = run.plan
        present = bool(plan and plan.steps)
        return self._checkpoint(
            "planner",
            "present" if present else "missing",
            f"Planner produced {len(plan.steps) if plan else 0} step(s)." if present else "Planner did not produce executable steps.",
            evidence_refs=[{"kind": "task_run_plan", "source_id": plan.plan_id, "status": plan.status}] if plan else [],
        )

    def _contract_checkpoint(self, run: TaskRun) -> ToolGovernanceCheckpoint:
        present = bool(run.contract_type and run.runtime_profile)
        return self._checkpoint(
            "contract",
            "present" if present else "missing",
            "Contract type and runtime profile are set." if present else "Contract type or runtime profile is missing.",
            evidence_refs=[{"kind": "contract", "contract_type": run.contract_type, "runtime_profile": run.runtime_profile}],
        )

    def _capability_checkpoint(self, run: TaskRun) -> ToolGovernanceCheckpoint:
        values = list(dict.fromkeys([*run.capabilities_required, *run.requested_actions]))
        present = bool(values) or bool(run.plan and run.plan.steps)
        return self._checkpoint(
            "capability",
            "present" if present else "missing",
            "Capabilities/actions are derivable from request or runtime steps." if present else "No capabilities or actions are defined.",
            evidence_refs=[{"kind": "capabilities", "values": values}],
        )

    def _policy_checkpoint(self, run: TaskRun) -> ToolGovernanceCheckpoint:
        policy = run.policy_snapshot if isinstance(run.policy_snapshot, dict) else {}
        present = bool(policy)
        blocked = str(policy.get("status") or policy.get("policy_status") or "").lower() in {"blocked", "denied"}
        status = "blocked" if blocked else "present" if present else "missing"
        return self._checkpoint(
            "policy",
            status,
            "Policy snapshot is available." if present else "Policy snapshot is missing.",
            evidence_refs=[{"kind": "policy_snapshot", "value": self._sanitize_small(policy)}] if present else [],
        )

    def _approval_checkpoint(self, run: TaskRun) -> ToolGovernanceCheckpoint:
        required_for = self._approval_required_for(run)
        if not required_for:
            return self._checkpoint(
                "approval",
                "not_required",
                "Policy snapshot does not require explicit approval for requested actions.",
                required=False,
            )
        if run.approval_id:
            return self._checkpoint(
                "approval",
                "present",
                "Approval is linked to this run.",
                evidence_refs=[{"kind": "approval", "approval_id": run.approval_id}],
            )
        return self._checkpoint(
            "approval",
            "blocked",
            "Policy requires approval but the run has no approval_id.",
            evidence_refs=[{"kind": "approval_required_for", "values": required_for}],
        )

    def _tool_router_checkpoint(self, run: TaskRun) -> ToolGovernanceCheckpoint:
        graph = run.execution_graph
        routes = []
        if graph:
            for node in graph.nodes:
                route = node.validation_gate.get("worker_route") if isinstance(node.validation_gate, dict) else None
                if route:
                    routes.append({"node_id": node.node_id, "step_id": node.step_id, "worker": node.worker, "route": route})
        present = bool(routes)
        return self._checkpoint(
            "tool_router",
            "present" if present else "missing",
            f"Tool router has {len(routes)} worker route decision(s)." if present else "No worker route decision was recorded.",
            evidence_refs=routes,
        )

    def _execution_checkpoint(self, run: TaskRun) -> ToolGovernanceCheckpoint:
        if run.status == "blocked":
            return self._checkpoint(
                "execution",
                "blocked",
                "TaskRun is blocked before or during execution.",
                evidence_refs=[{"kind": "task_run", "status": run.status, "blocked_reasons": run.blocked_reasons}],
            )
        present = bool(run.status)
        return self._checkpoint(
            "execution",
            "present" if present else "missing",
            f"TaskRun execution lifecycle status is {run.status}." if present else "TaskRun status is missing.",
            evidence_refs=[{"kind": "task_run", "status": run.status, "current_step_id": run.current_step_id}],
        )

    def _validation_checkpoint(self, run: TaskRun, result: TaskRunResult | None) -> ToolGovernanceCheckpoint:
        if result and result.validation:
            status = str(result.validation.get("status") or result.validation.get("validation_status") or result.status)
            if result.completion and not result.completion.safe_to_report_success:
                return self._checkpoint(
                    "validation",
                    "blocked",
                    "Completion gate does not allow success reporting.",
                    evidence_refs=[{"kind": "completion", "value": result.completion.model_dump()}],
                )
            return self._checkpoint(
                "validation",
                "present",
                f"Validation result is available with status {status}.",
                evidence_refs=[{"kind": "validation_result", "value": self._sanitize_small(result.validation)}],
            )
        if result and result.status in {"blocked", "failed", "cancelled"}:
            return self._checkpoint(
                "validation",
                "blocked",
                f"Terminal result is {result.status}; operational validation cannot pass.",
                evidence_refs=[{"kind": "task_run_result", "status": result.status}],
            )
        if run.status in {"created", "queued", "waiting_input"}:
            return self._checkpoint(
                "validation",
                "pending",
                "Validation is pending until execution reaches a terminal state.",
                required=False,
            )
        return self._checkpoint(
            "validation",
            "missing",
            "No validation evidence is available for a terminal or active run.",
        )

    def _artifacts_checkpoint(self, run: TaskRun, result: TaskRunResult | None) -> ToolGovernanceCheckpoint:
        artifact_required = self._artifact_required(run)
        artifact_refs = []
        if result:
            outputs = result.outputs if isinstance(result.outputs, dict) else {}
            for key in ("artifacts", "artifact_links", "artifact_ids", "reports"):
                value = outputs.get(key)
                if value:
                    artifact_refs.append({"kind": key, "value": self._sanitize_small(value)})
        if artifact_refs:
            return self._checkpoint("artifacts", "present", "Artifact/report evidence is available.", evidence_refs=artifact_refs)
        if not artifact_required:
            return self._checkpoint("artifacts", "not_required", "No artifact-producing action is requested.", required=False)
        if run.status in {"created", "queued", "waiting_input"}:
            return self._checkpoint("artifacts", "pending", "Artifact generation is pending execution.", required=False)
        return self._checkpoint("artifacts", "missing", "Artifact-producing action has no artifact evidence.")

    def _report_checkpoint(self, run: TaskRun, result: TaskRunResult | None) -> ToolGovernanceCheckpoint:
        if result:
            return self._checkpoint(
                "report",
                "present",
                "TaskRunResult is available as terminal report.",
                evidence_refs=[{"kind": "task_run_result", "status": result.status, "trace_ref": result.trace_ref}],
            )
        if run.status in {"created", "queued", "waiting_input"}:
            return self._checkpoint("report", "pending", "Terminal report is pending execution.", required=False)
        return self._checkpoint("report", "missing", "Terminal report is missing.")

    def _checkpoint(
        self,
        stage: ToolGovernanceStage,
        status: str,
        summary: str,
        *,
        evidence_refs: list[dict[str, Any]] | None = None,
        required: bool = True,
    ) -> ToolGovernanceCheckpoint:
        return ToolGovernanceCheckpoint(
            stage=stage,
            status=status,  # type: ignore[arg-type]
            summary=summary,
            evidence_refs=evidence_refs or [],
            required=required,
        )

    def _approval_required_for(self, run: TaskRun) -> list[str]:
        policy = run.policy_snapshot if isinstance(run.policy_snapshot, dict) else {}
        required = list(policy.get("approval_required_for", []) or [])
        return [str(item) for item in required if str(item) in set(run.requested_actions or required)]

    def _side_effect_requested(self, run: TaskRun) -> bool:
        actions = {str(action) for action in run.requested_actions}
        return bool(actions.intersection(self.SIDE_EFFECT_ACTIONS)) or any(step.side_effect for step in run.plan.steps)

    def _artifact_required(self, run: TaskRun) -> bool:
        actions = {str(action) for action in run.requested_actions}
        if actions.intersection(self.ARTIFACT_ACTIONS):
            return True
        if run.execution_graph:
            return any(node.artifacts_expected for node in run.execution_graph.nodes)
        return False

    def _has_execution_plan(self, run: TaskRun) -> bool:
        return bool(run.plan and run.plan.steps and run.execution_graph and run.execution_graph.nodes)

    def _primary_action(self, run: TaskRun) -> str | None:
        if run.requested_actions:
            return str(run.requested_actions[0])
        if run.plan and run.plan.steps:
            return run.plan.steps[0].action
        return None

    def _result_has_operational_evidence(self, result: TaskRunResult) -> bool:
        return bool(result.outputs or result.step_summaries or result.validation or result.completion)

    def _sanitize_small(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._sanitize_small(item) for key, item in list(value.items())[:20]}
        if isinstance(value, list):
            return [self._sanitize_small(item) for item in value[:20]]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
