from __future__ import annotations
from uuid import uuid4
from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.runtime.task_run_trace_service import TaskRunTraceService
from aipinho.services.runtime.runtime_profile_service import RuntimeProfileService
from aipinho.services.runtime.execution_plan_promotion_service import ExecutionPlanPromotionService
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.utils.yaml_loader import load_yaml_file

class TaskRunPlanner:
    def __init__(self) -> None:
        self.runtime = load_yaml_file(PATHS.config_root / "runtime" / "task_runtime_policy.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.steps = load_yaml_file(PATHS.config_root / "runtime" / "governed_task_steps.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.profiles = RuntimeProfileService().load()
        self.actions = ActionRegistryService().load()
        self.limits = load_yaml_file(PATHS.config_root / "runtime" / "task_runtime_limits.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.trace = TaskRunTraceService()
        self.execution_plans = ExecutionPlanPromotionService()

    def plan(self, request: TaskRunRequest) -> TaskRunPlan:
        allowed_contracts = set(self.runtime.get("allowed_contract_types", []) or [])
        allowed_actions = set(self.runtime.get("allowed_actions", []) or [])
        blocked_actions = set(self.runtime.get("blocked_actions", []) or [])
        reasons: list[str] = []
        if request.contract_type not in allowed_contracts: reasons.append("unsupported_contract_type")
        normalized_actions = [
            self.actions.normalize_action(action) if self.actions.action_exists(action) else action
            for action in request.requested_actions
        ]
        for action in normalized_actions:
            if action in blocked_actions: reasons.append(f"blocked_action:{action}")
            elif action not in allowed_actions: reasons.append(f"unknown_runtime_action:{action}")
        profile = self.profiles.resolve(
            operation_type=request.operation_type,
            contract_type=request.contract_type,
            requested_profile=request.runtime_profile,
        )
        if profile is None:
            reasons.append("runtime_profile_missing")
            profile = {}
        step_ids = list(profile.get("steps", []) or []) if not reasons else []
        max_steps = int(self.limits.get("limits", {}).get("max_steps_per_run", 20))
        if not step_ids: reasons.append("runtime_pipeline_missing")
        if len(step_ids) > max_steps: reasons.append("runtime_step_limit_exceeded")
        built: list[TaskRunStep] = []
        definitions = self.steps.get("step_types", {}) if isinstance(self.steps.get("step_types", {}), dict) else {}
        profile_actions = {
            str((definitions.get(step_id) or {}).get("action"))
            for step_id in step_ids
            if isinstance(definitions.get(step_id), dict)
        }
        profile_actions.update(str(action) for action in profile.get("allowed_actions", []) or [])
        for action in normalized_actions:
            if profile_actions and action not in profile_actions:
                reasons.append(f"action_not_allowed_by_profile:{action}")
        for index, step_type in enumerate(step_ids):
            definition = definitions.get(step_type)
            if not isinstance(definition, dict) or not definition.get("enabled", False):
                reasons.append(f"unknown_or_disabled_step:{step_type}")
                continue
            action = str(definition.get("action", ""))
            side_effect = bool(definition.get("side_effect", False))
            if action not in allowed_actions:
                reasons.append(f"action_not_allowed:{action}")
                continue
            if side_effect and not profile.get("allowed_side_effects"):
                reasons.append(f"profile_side_effect_not_allowed:{step_type}")
                continue
            built.append(TaskRunStep(step_id=f"step_{index+1:02d}_{step_type}", step_type=step_type, action=action, required=bool(definition.get("required", True)), side_effect=side_effect))
        status = "blocked" if reasons else "ready"
        task_plan = TaskRunPlan(
            plan_id=f"task_run_plan_{uuid4().hex}",
            contract_type=request.contract_type,
            status=status,
            steps=built,
            blocked_reasons=list(dict.fromkeys(reasons)),
            trace=[self.trace.item("task_run_planner", status, "plan_built_from_runtime_profile", source=f"config/runtime/profiles/{profile.get('id', 'missing')}.yaml", data={"steps": len(built), "profile": profile.get("id")})],
            metadata={
                "runtime_profile": profile.get("id"),
                "required_capabilities": list(profile.get("required_capabilities", []) or []),
                "approval_scope": profile.get("approval_scope"),
                "output_validation_required": bool(profile.get("output_validation_required", False)),
                "artifact_registration_required": bool(profile.get("artifact_registration_required", False)),
                "normalized_actions": normalized_actions,
                "workspace_requirements": dict(profile.get("workspace_requirements", {}) or {}),
            },
        )
        candidate = self.execution_plans.candidate_from_task_run_plan(
            request=request,
            plan=task_plan,
            workspace_context={"workspace_path": request.workspace} if request.workspace else {},
        )
        promotion = self.execution_plans.promote(
            candidate,
            policy_snapshot=request.policy_decision,
            task_id=request.task_id,
            taskrun_id=request.task_run_id,
            approval_id=request.approval_id,
        )
        task_plan.candidate_plan = candidate
        task_plan.canonical_execution_plan = promotion.execution_plan
        task_plan.metadata["candidate_plan_id"] = candidate.candidate_plan_id
        if promotion.execution_plan is not None:
            task_plan.metadata["execution_id"] = promotion.execution_plan.execution_id
            task_plan.metadata["canonical_execution_plan"] = promotion.execution_plan.model_dump(mode="json")
        if promotion.reason_codes:
            task_plan.status = "blocked"
            task_plan.blocked_reasons = list(dict.fromkeys([*task_plan.blocked_reasons, *promotion.reason_codes]))
        task_plan.trace.append(
            self.trace.item(
                "execution_plan_promotion",
                promotion.status,
                "candidate_plan_promoted_by_effective_policy",
                source="services/runtime/execution_plan_promotion_service.py",
                data={
                    "candidate_plan_id": candidate.candidate_plan_id,
                    "execution_id": promotion.execution_plan.execution_id if promotion.execution_plan else None,
                    "reason_codes": promotion.reason_codes,
                },
            )
        )
        return task_plan

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_run_planner", "profiles": self.profiles.status()}
