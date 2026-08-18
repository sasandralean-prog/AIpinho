from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.execution_plan import (
    CandidatePlan,
    CanonicalExecutionPlan,
    CanonicalExecutionStep,
    ExecutionPlanPromotionDecision,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_request import TaskRunRequest


class ExecutionPlanPromotionService:
    """Canonical boundary from planning output to executable runtime contract."""

    SIDE_EFFECT_ACTIONS = {
        "write_files",
        "apply_patch",
        "patch_apply",
        "run_command",
        "run_tests",
        "delete_files",
        "move_files",
    }

    def candidate_from_task_run_plan(
        self,
        *,
        request: TaskRunRequest,
        plan: TaskRunPlan,
        workspace_context: dict[str, Any] | None = None,
    ) -> CandidatePlan:
        workspace_data = dict(workspace_context or {})
        workspace_path = request.workspace or workspace_data.get("workspace_path") or workspace_data.get("project_root")
        if workspace_path:
            workspace_data.setdefault("workspace_path", workspace_path)
            workspace_data.setdefault("project_root", workspace_path)
        steps = [
            CanonicalExecutionStep(
                step_id=step.step_id,
                step_type=step.step_type,
                action=step.action,
                required=step.required,
                side_effect=step.side_effect,
                inputs=self._step_inputs(request, step),
                expected_outputs=list(getattr(step, "expected_outputs", []) or []),
                required_capabilities=list(plan.metadata.get("required_capabilities", []) or []),
                metadata={"source_step_type": step.step_type},
            )
            for step in plan.steps
        ]
        return CandidatePlan(
            semantic_goal=self._semantic_goal(request),
            operation_kind=str(request.operation_type or request.contract_type),
            workspace=workspace_data,
            targets=self._targets(request, workspace_data),
            dependencies=self._dependencies(request),
            requested_actions=list(plan.metadata.get("normalized_actions", []) or request.requested_actions),
            required_capabilities=list(plan.metadata.get("required_capabilities", []) or request.capabilities_required),
            execution_steps=steps,
            rollback_strategy=self._rollback_strategy(request, steps),
            validation_requirements=self._validation_requirements(request, plan),
            artifact_expectations=self._artifact_expectations(request),
            source_ref=plan.plan_id,
            metadata={
                "contract_type": request.contract_type,
                "runtime_profile": plan.metadata.get("runtime_profile") or request.runtime_profile,
                "source": "task_run_planner",
                "requested_deliverables": self._requested_deliverables(request),
                "workspace_references": self._workspace_references(request),
            },
        )

    def promote(
        self,
        candidate: CandidatePlan,
        *,
        policy_snapshot: dict[str, Any] | None = None,
        task_id: str | None = None,
        taskrun_id: str | None = None,
        approval_id: str | None = None,
    ) -> ExecutionPlanPromotionDecision:
        policy = dict(policy_snapshot or {})
        reasons = self._promotion_reasons(candidate, policy)
        status = "blocked" if reasons else "ready"
        approval_required = bool(
            set(policy.get("approval_required_for", []) or []).intersection(candidate.requested_actions)
            or any(step.side_effect for step in candidate.execution_steps)
        )
        execution_plan = CanonicalExecutionPlan(
            candidate_plan_id=candidate.candidate_plan_id,
            task_id=task_id,
            taskrun_id=taskrun_id,
            semantic_goal=candidate.semantic_goal,
            operation_kind=candidate.operation_kind,
            workspace=dict(candidate.workspace),
            targets=list(candidate.targets),
            dependencies=list(candidate.dependencies),
            policy_snapshot=policy,
            approval_required=approval_required,
            approval_id=approval_id,
            execution_steps=list(candidate.execution_steps),
            rollback_strategy=dict(candidate.rollback_strategy),
            validation_requirements=list(candidate.validation_requirements),
            artifact_expectations=list(candidate.artifact_expectations),
            required_capabilities=list(candidate.required_capabilities),
            trace_id=candidate.trace_id,
            status=status,
            blocked_reasons=reasons,
            metadata=dict(candidate.metadata),
        )
        return ExecutionPlanPromotionDecision(
            status="rejected" if reasons else "promoted",
            candidate_plan_id=candidate.candidate_plan_id,
            execution_plan=execution_plan,
            reason_codes=reasons,
            policy_snapshot=policy,
            trace=[
                {
                    "stage": "execution_plan_promotion",
                    "status": "rejected" if reasons else "promoted",
                    "reason_codes": reasons,
                    "source": "services/runtime/execution_plan_promotion_service.py",
                }
            ],
        )

    def bind_runtime_identity(
        self,
        plan: CanonicalExecutionPlan,
        *,
        task_id: str | None,
        taskrun_id: str | None,
        approval_id: str | None = None,
    ) -> CanonicalExecutionPlan:
        updated = plan.model_copy(deep=True)
        updated.task_id = task_id
        updated.taskrun_id = taskrun_id
        if approval_id:
            updated.approval_id = approval_id
        return updated

    def _promotion_reasons(self, candidate: CandidatePlan, policy: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        if not candidate.execution_steps:
            reasons.append("candidate_plan_has_no_execution_steps")
        if any(step.side_effect for step in candidate.execution_steps):
            if not candidate.targets:
                reasons.append("side_effect_execution_requires_targets")
            if not candidate.rollback_strategy:
                reasons.append("side_effect_execution_requires_rollback_strategy")
        denied = set(policy.get("denied_actions", []) or [])
        for action in candidate.requested_actions:
            if action in denied:
                reasons.append(f"action_denied_by_policy:{action}")
        return list(dict.fromkeys(reasons))

    def _semantic_goal(self, request: TaskRunRequest) -> str:
        intent = request.intent_map if isinstance(request.intent_map, dict) else {}
        for key in ("semantic_goal", "goal", "summary", "intent_type"):
            if intent.get(key):
                return str(intent[key])
        return str(request.operation_type or request.contract_type)

    def _targets(self, request: TaskRunRequest, workspace_data: dict[str, Any]) -> list[str]:
        candidates = list(getattr(request, "target_paths", []) or [])
        if not candidates and isinstance(request.intent_map, dict):
            candidates.extend(str(item) for item in request.intent_map.get("target_paths", []) or [])
        if not candidates and set(request.requested_actions).intersection(self.SIDE_EFFECT_ACTIONS):
            workspace = workspace_data.get("workspace_path") or request.workspace
            if workspace:
                candidates.append(str(workspace))
        return list(dict.fromkeys(item for item in candidates if item))

    def _dependencies(self, request: TaskRunRequest) -> list[dict[str, Any]]:
        dependencies = []
        if request.parent_task_id:
            dependencies.append({"type": "parent_task", "id": request.parent_task_id})
        if request.context_injection_plan_id:
            dependencies.append({"type": "context_injection_plan", "id": request.context_injection_plan_id})
        return dependencies

    def _rollback_strategy(self, request: TaskRunRequest, steps: list[CanonicalExecutionStep]) -> dict[str, Any]:
        if not any(step.side_effect for step in steps):
            return {"required": False}
        return {
            "required": True,
            "strategy": "runtime_snapshot_or_patch_backup",
            "source": "canonical_execution_plan",
            "workspace": request.workspace,
        }

    def _validation_requirements(self, request: TaskRunRequest, plan: TaskRunPlan) -> list[str]:
        requirements = list(getattr(request, "expected_outputs", []) or [])
        if plan.metadata.get("output_validation_required"):
            requirements.append("output_validation")
        if plan.metadata.get("artifact_registration_required"):
            requirements.append("artifact_registration")
        return list(dict.fromkeys(str(item) for item in requirements if item))

    def _artifact_expectations(self, request: TaskRunRequest) -> list[str]:
        intent = request.intent_map if isinstance(request.intent_map, dict) else {}
        values = list(getattr(request, "expected_artifacts", []) or [])
        values.extend(str(item) for item in intent.get("logical_artifact_paths", []) or [])
        return list(dict.fromkeys(item for item in values if item))

    def _step_inputs(self, request: TaskRunRequest, step: Any) -> dict[str, Any]:
        inputs = dict(getattr(step, "input_summary", {}) or {})
        intent = request.intent_map if isinstance(request.intent_map, dict) else {}
        shell_plan = intent.get("shell_plan")
        if step.action in {"run_command", "shell"} and isinstance(shell_plan, dict) and shell_plan:
            inputs.setdefault("shell_plan", shell_plan)
        patch_plan = intent.get("patch_plan")
        if step.action in {"apply_patch", "patch_apply"} and isinstance(patch_plan, dict) and patch_plan:
            inputs.setdefault("patch_plan", patch_plan)
        return inputs

    def _requested_deliverables(self, request: TaskRunRequest) -> list[str]:
        intent = request.intent_map if isinstance(request.intent_map, dict) else {}
        return [str(item) for item in intent.get("requested_deliverables", []) or [] if item]

    def _workspace_references(self, request: TaskRunRequest) -> list[str]:
        intent = request.intent_map if isinstance(request.intent_map, dict) else {}
        return [str(item) for item in intent.get("workspace_references", []) or [] if item]
