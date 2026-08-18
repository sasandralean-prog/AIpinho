from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import Field
from aipinho.core.paths import PATHS
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.schemas.runtime.task_run_trace import TaskRunTraceItem
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.services.runtime.runtime_profile_service import RuntimeProfileService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_trace_service import TaskRunTraceService
from aipinho.utils.yaml_loader import load_yaml_file

class TaskRunGuardDecision(AIpinhoModel):
    allowed: bool
    status: str
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[TaskRunTraceItem] = Field(default_factory=list)

class TaskRunGuard:
    def __init__(self, workspace_policy: WorkspacePolicyService | None = None, approvals: ApprovalService | None = None, lifecycle: TaskRunLifecycleService | None = None, workspace_roles: WorkspaceRoleContractService | None = None, profiles: RuntimeProfileService | None = None, permission_matrix: WorkspacePermissionMatrixService | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "runtime" / "task_runtime_policy.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.steps = load_yaml_file(PATHS.config_root / "runtime" / "governed_task_steps.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.limits = load_yaml_file(PATHS.config_root / "runtime" / "task_runtime_limits.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.workspace_policy = workspace_policy or WorkspacePolicyService().load()
        self.workspace_roles = workspace_roles or WorkspaceRoleContractService().load()
        self.permission_matrix = permission_matrix or WorkspacePermissionMatrixService().load()
        self.profiles = profiles or RuntimeProfileService().load()
        self.approvals = approvals or ApprovalService()
        self.lifecycle = lifecycle or TaskRunLifecycleService()
        self.trace_service = TaskRunTraceService()

    def check_run(self, run: TaskRun) -> TaskRunGuardDecision:
        reasons: list[str] = []
        settings = self.policy.get("task_runtime", {}) if isinstance(self.policy.get("task_runtime", {}), dict) else {}
        if not settings.get("enabled", False): reasons.append("task_runtime_disabled")
        if not run.task_id:
            reasons.append("missing_task_id")
        if not run.task_run_id:
            reasons.append("missing_task_run_id")
        if run.task_run_id and run.task_run_id != run.run_id:
            reasons.append("task_run_id_mismatch")
        if not run.operation_id:
            reasons.append("missing_operation_id")
        bootstrap_context = run.bootstrap_context if isinstance(run.bootstrap_context, dict) else {}
        if not bootstrap_context:
            reasons.append("missing_bootstrap_context")
        else:
            if bootstrap_context.get("task_id") != run.task_id:
                reasons.append("bootstrap_task_id_mismatch")
            if bootstrap_context.get("task_run_id") != run.task_run_id:
                reasons.append("bootstrap_task_run_id_mismatch")
            if bootstrap_context.get("operation_id") != run.operation_id:
                reasons.append("bootstrap_operation_id_mismatch")
        if not run.policy_snapshot: reasons.append("missing_policy_decision")
        policy_status = str(run.policy_snapshot.get("status") or run.policy_snapshot.get("policy_status") or "")
        if policy_status in {"denied", "blocked", ""}: reasons.append("policy_decision_not_allowed")
        profile = self._profile(run)
        if profile is None:
            reasons.append("runtime_profile_missing")
            profile = {}
        execution_plan = run.plan.canonical_execution_plan
        if execution_plan is None:
            reasons.append("missing_canonical_execution_plan")
        else:
            if execution_plan.taskrun_id and execution_plan.taskrun_id != run.run_id:
                reasons.append("execution_plan_task_run_mismatch")
            if execution_plan.task_id and execution_plan.task_id != run.task_id:
                reasons.append("execution_plan_task_id_mismatch")
            if execution_plan.status == "blocked":
                reasons.extend(execution_plan.blocked_reasons or ["execution_plan_blocked"])
        readonly_unregistered_allowed = self._readonly_unregistered_allowed(run, profile)
        requirements = profile.get("workspace_requirements", {}) if isinstance(profile.get("workspace_requirements", {}), dict) else {}
        workspace_required = bool(requirements.get("required", False))
        if workspace_required and not run.workspace: reasons.append("workspace_required")
        workspace = self.workspace_policy.evaluate(workspace_path=run.workspace, requires_workspace=workspace_required)
        if workspace.blocked: reasons.append("forbidden_root")
        if workspace.needs_clarification: reasons.append("workspace_needs_clarification")
        role_decision = self.workspace_roles.resolve(run.workspace, required=workspace_required)
        if role_decision.status == "denied" and not (readonly_unregistered_allowed and role_decision.reason == "workspace_not_registered"):
            reasons.append(role_decision.reason)
        if role_decision.status == "needs_clarification": reasons.append(role_decision.reason)
        allowed_roles = set(requirements.get("allowed_roles", []) or [])
        if (
            role_decision.contract is not None
            and allowed_roles
            and role_decision.contract.role not in allowed_roles
            and not (readonly_unregistered_allowed and role_decision.reason == "workspace_not_registered")
        ):
            reasons.append(f"workspace_role_not_allowed:{role_decision.contract.role}")
        allowed = set(self.policy.get("allowed_actions", []) or [])
        blocked = set(self.policy.get("blocked_actions", []) or [])
        policy_allowed = set(run.policy_snapshot.get("allowed_actions", []) or [])
        policy_denied = set(run.policy_snapshot.get("denied_actions", []) or [])
        approvals_required = set(run.policy_snapshot.get("approval_required_for", []) or [])
        existing_approval = self.approvals.get_approval(run.approval_id) if run.approval_id else None
        approval_is_approved = existing_approval is not None and existing_approval.status == "approved"
        if existing_approval is not None and execution_plan is not None:
            if not existing_approval.execution_id:
                reasons.append("approval_missing_execution_plan_binding")
            elif existing_approval.execution_id != execution_plan.execution_id:
                reasons.append("approval_execution_plan_mismatch")
        matrix_approval_required = False
        for action in run.requested_actions:
            if not run.workspace:
                continue
            matrix_decision = self.permission_matrix.decide(path=run.workspace, permission=action)
            if matrix_decision.status == "denied":
                if readonly_unregistered_allowed and self._readonly_action_allowed_for_unregistered(action, matrix_decision.reason_code):
                    continue
                reasons.append(f"{matrix_decision.reason_code}:{action}")
            elif matrix_decision.status == "approval_required" and not approval_is_approved:
                matrix_approval_required = True
                reasons.append(f"{matrix_decision.reason_code}:{action}")
        for action in run.requested_actions:
            if action in blocked: reasons.append(self._blocked_reason(action))
            elif action not in allowed: reasons.append(f"action_not_allowed:{action}")
            elif action in policy_denied: reasons.append(f"action_denied_by_policy:{action}")
            elif policy_allowed and action not in policy_allowed and action not in approvals_required: reasons.append(f"action_not_granted_by_policy:{action}")
            elif action not in self._profile_actions(profile): reasons.append(f"action_not_allowed_by_profile:{action}")
        denied_capabilities = set(run.policy_snapshot.get("denied_capabilities", []) or [])
        required_capabilities = set(run.capabilities_required or profile.get("required_capabilities", []) or [])
        for capability in required_capabilities.intersection(denied_capabilities):
            reasons.append(f"capability_denied:{capability}")
        side_effect_plan = any(step.side_effect for step in run.plan.steps)
        if side_effect_plan and execution_plan is not None and not execution_plan.approval_required:
            reasons.append("side_effect_execution_plan_requires_approval")
        if approvals_required.intersection(run.requested_actions) or matrix_approval_required:
            approval = existing_approval
            if approval is None or approval.status == "pending":
                reasons.append("approval_required")
            elif approval.status != "approved":
                reasons.append("approval_denied")
        if run.cancellation_requested: reasons.append("cancellation_requested")
        if self.lifecycle.is_terminal(run.status): reasons.append("task_run_terminal")
        return self._decision(reasons, "run_guard_checked")

    def check_step(self, run: TaskRun, step: TaskRunStep, *, step_index: int, elapsed_seconds: float) -> TaskRunGuardDecision:
        reasons: list[str] = []
        if run.cancellation_requested: reasons.append("cancellation_requested")
        profile = self._profile(run) or {}
        allowed_step_types = set(profile.get("allowed_step_types", []) or [])
        if allowed_step_types and step.step_type not in allowed_step_types:
            reasons.append(f"step_not_allowed_by_profile:{step.step_type}")
        if step.side_effect and not profile.get("allowed_side_effects"):
            reasons.append("side_effect_not_allowed_by_profile")
        allowed = set(self.policy.get("allowed_actions", []) or [])
        blocked = set(self.policy.get("blocked_actions", []) or [])
        if step.action in blocked: reasons.append(self._blocked_reason(step.action))
        elif step.action not in allowed: reasons.append(f"action_not_allowed:{step.action}")
        max_steps = int(self.limits.get("limits", {}).get("max_steps_per_run", 20))
        if step_index >= max_steps: reasons.append("step_limit_exceeded")
        max_seconds = self._max_runtime_seconds(profile)
        if elapsed_seconds > max_seconds: reasons.append("runtime_timeout_exceeded")
        return self._decision(reasons, "step_guard_checked", step_id=step.step_id)

    def _profile(self, run: TaskRun) -> dict[str, Any] | None:
        return self.profiles.resolve(
            operation_type=run.operation_type,
            contract_type=run.contract_type,
            requested_profile=run.runtime_profile,
        )

    def _profile_actions(self, profile: dict[str, Any]) -> set[str]:
        definitions = self.steps.get("step_types", {}) if isinstance(self.steps.get("step_types", {}), dict) else {}
        actions = {
            str((definitions.get(step_id) or {}).get("action"))
            for step_id in profile.get("steps", []) or []
            if isinstance(definitions.get(step_id), dict)
        }
        actions.update(str(action) for action in profile.get("allowed_actions", []) or [])
        return {item for item in actions if item}

    def _readonly_unregistered_allowed(self, run: TaskRun, profile: dict[str, Any]) -> bool:
        if not run.workspace:
            return False
        if profile.get("allowed_side_effects"):
            return False
        actions = set(run.requested_actions or [])
        if actions and not actions <= {"read_files", "read_workspace", "inspect_path", "list_directory", "project_tree", "project_context", "project_analysis", "project_report"}:
            return False
        markers = {
            str(run.contract_type or ""),
            str(run.operation_type or ""),
            str(run.runtime_profile or ""),
            str(run.intent_map.get("intent_type") if isinstance(run.intent_map, dict) else ""),
        }
        return bool(markers.intersection({"readonly_analysis", "analysis_readonly", "workspace_analysis_readonly"}))

    def _readonly_action_allowed_for_unregistered(self, action: str, reason_code: str | None) -> bool:
        return (
            str(reason_code or "") == "workspace_not_registered"
            and action in {"read_files", "read_workspace", "inspect_path", "list_directory", "project_tree", "project_context", "project_analysis", "project_report"}
        )

    def _max_runtime_seconds(self, profile: dict[str, Any]) -> float:
        profile_limit = profile.get("max_duration_seconds")
        if profile_limit is not None:
            try:
                return float(profile_limit)
            except (TypeError, ValueError):
                pass
        return float(self.limits.get("limits", {}).get("max_runtime_seconds", 180))

    def _blocked_reason(self, action: str) -> str:
        if action in {"write_files", "delete_files", "move_files"}: return "write_action_blocked"
        if action in {"apply_patch", "patch_apply"}: return "patch_action_blocked"
        if action in {"run_command", "shell"}: return "shell_action_blocked"
        return f"blocked_action:{action}"

    def _decision(self, reasons: list[str], reason: str, step_id: str | None = None) -> TaskRunGuardDecision:
        unique = list(dict.fromkeys(reasons))
        status = "blocked" if unique else "allowed"
        return TaskRunGuardDecision(allowed=not unique, status=status, blocked_reasons=unique, trace=[self.trace_service.item("task_run_guard", status, reason, step_id=step_id, source="services/runtime/task_run_guard.py", data={"blocked_reasons": unique})])

    def status(self) -> dict[str, object]:
        profile_status = self.profiles.status()
        available = set(profile_status.get("profiles", []) or [])
        return {
            "status": "ok" if profile_status.get("status") == "ok" else "degraded",
            "service": "task_run_guard",
            "mode": "capability_based_guarded_execution",
            "capabilities": {
                "write_file": {"enabled": "write_file" in available, "reason": "runtime_profile_loaded" if "write_file" in available else "runtime_profile_missing"},
                "patch_apply": {"enabled": "patch" in available, "reason": "runtime_profile_loaded" if "patch" in available else "runtime_profile_missing"},
                "shell_execute": {"enabled": "shell" in available, "reason": "runtime_profile_loaded" if "shell" in available else "runtime_profile_missing"},
                "web_search": {"enabled": "web_search" in available, "reason": "runtime_profile_loaded" if "web_search" in available else "runtime_profile_missing"},
                "artifact_zip": {"enabled": "artifact_generation" in available, "reason": "runtime_profile_loaded" if "artifact_generation" in available else "runtime_profile_missing"},
            },
        }
