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
from aipinho.schemas.governance.lifecycle import CanonicalOperationContract, CanonicalPermission, CanonicalPolicyDecision, CanonicalPolicyFacet
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
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
    canonical_policy_decisions: list[CanonicalPolicyDecision] = Field(default_factory=list)

class TaskRunGuard:
    def __init__(self, workspace_policy: WorkspacePolicyService | None = None, approvals: ApprovalService | None = None, lifecycle: TaskRunLifecycleService | None = None, workspace_roles: WorkspaceRoleContractService | None = None, profiles: RuntimeProfileService | None = None, permission_matrix: WorkspacePermissionMatrixService | None = None, authority_grants: AuthorityGrantService | None = None, effective_policy: EffectivePolicyDecisionService | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "runtime" / "task_runtime_policy.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.steps = load_yaml_file(PATHS.config_root / "runtime" / "governed_task_steps.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.limits = load_yaml_file(PATHS.config_root / "runtime" / "task_runtime_limits.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.workspace_policy = workspace_policy or WorkspacePolicyService().load()
        self.workspace_roles = workspace_roles or WorkspaceRoleContractService().load()
        self.permission_matrix = permission_matrix or WorkspacePermissionMatrixService().load()
        self.profiles = profiles or RuntimeProfileService().load()
        self.approvals = approvals or ApprovalService()
        self.authority_grants = authority_grants or AuthorityGrantService()
        self.effective_policy = effective_policy or EffectivePolicyDecisionService()
        self.lifecycle = lifecycle or TaskRunLifecycleService()
        self.trace_service = TaskRunTraceService()

    def check_run(self, run: TaskRun) -> TaskRunGuardDecision:
        reasons: list[str] = []
        canonical_decisions: list[CanonicalPolicyDecision] = []
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
        local_resources = (
            list(run.mission_contract.local_resources)
            if run.mission_contract is not None
            else []
        )
        readonly_unregistered_allowed = self._readonly_unregistered_allowed(run, profile)
        requirements = profile.get("workspace_requirements", {}) if isinstance(profile.get("workspace_requirements", {}), dict) else {}
        workspace_required = bool(requirements.get("required", False))
        if workspace_required and not run.workspace: reasons.append("workspace_required")
        workspace = self.workspace_policy.evaluate(workspace_path=run.workspace, requires_workspace=workspace_required)
        if workspace.blocked: reasons.append("forbidden_root")
        if workspace.needs_clarification: reasons.append("workspace_needs_clarification")
        role_decision = self.workspace_roles.resolve_with_resources(
            run.workspace,
            local_resources=local_resources,
            required=workspace_required,
        )
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
        for action in run.requested_actions:
            matrix_decision = None
            if run.workspace:
                matrix_decision = self.permission_matrix.decide_with_resources(
                    path=run.workspace,
                    permission=action,
                    local_resources=local_resources,
                )
                if (
                    readonly_unregistered_allowed
                    and matrix_decision.status == "denied"
                    and self._readonly_action_allowed_for_unregistered(action, matrix_decision.reason_code)
                ):
                    matrix_decision = None
            canonical = self._canonical_action_decision(
                run,
                action=action,
                matrix_decision=matrix_decision,
                profile=profile,
                allowed=allowed,
                blocked=blocked,
                policy_allowed=policy_allowed,
                policy_denied=policy_denied,
                approvals_required=approvals_required,
                existing_approval=existing_approval,
            )
            canonical_decisions.append(canonical)
            reason = self._legacy_reason_from_canonical(canonical, action=action)
            if reason:
                reasons.append(reason)
        denied_capabilities = set(run.policy_snapshot.get("denied_capabilities", []) or [])
        required_capabilities = set(run.capabilities_required or profile.get("required_capabilities", []) or [])
        for capability in required_capabilities.intersection(denied_capabilities):
            reasons.append(f"capability_denied:{capability}")
        side_effect_plan = any(step.side_effect for step in run.plan.steps)
        if side_effect_plan and execution_plan is not None and not execution_plan.approval_required:
            reasons.append("side_effect_execution_plan_requires_approval")
        if run.cancellation_requested: reasons.append("cancellation_requested")
        if self.lifecycle.is_terminal(run.status): reasons.append("task_run_terminal")
        return self._decision(reasons, "run_guard_checked", canonical_policy_decisions=canonical_decisions)

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

    def _mission_authority_allows(
        self,
        run: TaskRun,
        *,
        action: str,
        path: str | None = None,
        resource_id: str | None = None,
        repository_identity: str | None = None,
        branch: str | None = None,
    ) -> bool:
        contract = run.mission_contract
        if contract is None or action not in set(contract.authority.authorized_capabilities):
            return False
        decision = self.authority_grants.decision_for_contract(
            contract,
            action=action,
            path=path,
            resource_id=resource_id,
            repository_identity=repository_identity,
            branch=branch,
        )
        return decision is not None and decision.reason_code == "grant_effective"

    def _capability_for_action(self, run: TaskRun, action: str, matrix_decision: Any | None) -> str:
        if action == "run_command" and isinstance(run.intent_map, dict):
            shell_plan = run.intent_map.get("shell_plan")
            git_info = shell_plan.get("git_classification") if isinstance(shell_plan, dict) else None
            if isinstance(git_info, dict) and git_info.get("capability"):
                return str(git_info["capability"])
        return str(
            matrix_decision.permission
            if matrix_decision is not None
            else self.permission_matrix.permission_for_action(action)
        )

    def _git_authority_scope(self, run: TaskRun, action: str, capability: str):
        if action != "run_command" or run.mission_contract is None or not isinstance(run.intent_map, dict):
            return None, None, None
        shell_plan = run.intent_map.get("shell_plan")
        git_info = shell_plan.get("git_classification") if isinstance(shell_plan, dict) else None
        if not isinstance(git_info, dict):
            return None, None, None
        candidates = [
            item for item in run.mission_contract.remote_resources
            if item.role != "remote_denied" and capability in set(item.permissions)
        ]
        if len(candidates) != 1:
            return None, None, None
        resource = candidates[0]
        branch = str(git_info.get("branch") or "").strip() or None
        if branch is None and len(resource.allowed_branches) == 1:
            branch = resource.allowed_branches[0]
        return resource.resource_id, resource.normalized_identity, branch

    def _canonical_action_decision(
        self,
        run: TaskRun,
        *,
        action: str,
        matrix_decision: Any | None,
        profile: dict[str, Any],
        allowed: set[str],
        blocked: set[str],
        policy_allowed: set[str],
        policy_denied: set[str],
        approvals_required: set[str],
        existing_approval: Any | None,
    ) -> CanonicalPolicyDecision:
        capability = self._capability_for_action(run, action, matrix_decision)
        resource_id = matrix_decision.workspace_id if matrix_decision is not None else None
        authority_resource_id, repository_identity, git_branch = self._git_authority_scope(
            run, action, capability
        )
        facets: list[CanonicalPolicyFacet] = [
            CanonicalPolicyFacet(
                facet="capability_demand",
                permission=CanonicalPermission.ALLOWED,
                source="task_run.requested_actions",
                reason_code="capability_requested",
                capability=capability,
                resource_id=resource_id,
                details={"action": action},
            )
        ]
        resource_requires_human = False
        if matrix_decision is not None:
            resource_permission = (
                CanonicalPermission.DENIED
                if matrix_decision.status == "denied"
                else CanonicalPermission.ASK
                if matrix_decision.status == "approval_required"
                else CanonicalPermission.ALLOWED
            )
            resource_requires_human = matrix_decision.status == "approval_required"
            facets.append(
                CanonicalPolicyFacet(
                    facet="resource_permission",
                    permission=resource_permission,
                    source="workspace_permission_matrix",
                    reason_code=(
                        f"{matrix_decision.reason_code}:{action}"
                        if matrix_decision.status == "denied"
                        else str(matrix_decision.reason_code)
                    ),
                    capability=capability,
                    resource_id=resource_id,
                    requires_human_authority=resource_requires_human,
                    details={
                        "workspace_role": matrix_decision.workspace_role,
                        "permission_value": matrix_decision.permission_value,
                    },
                    trace=list(matrix_decision.trace),
                )
            )

        static_reason = None
        if action in blocked:
            static_reason = self._blocked_reason(action)
        elif action not in allowed:
            static_reason = f"action_not_allowed:{action}"
        facets.append(
            CanonicalPolicyFacet(
                facet="global_policy",
                permission=CanonicalPermission.DENIED if static_reason else CanonicalPermission.ALLOWED,
                source="task_runtime_policy",
                reason_code=static_reason or "action_allowed_by_runtime_policy",
                capability=capability,
                resource_id=resource_id,
            )
        )

        snapshot_reason = None
        if action in policy_denied:
            snapshot_reason = f"action_denied_by_policy:{action}"
        elif policy_allowed and action not in policy_allowed and action not in approvals_required:
            snapshot_reason = f"action_not_granted_by_policy:{action}"
        facets.append(
            CanonicalPolicyFacet(
                facet="policy_snapshot",
                permission=CanonicalPermission.DENIED if snapshot_reason else CanonicalPermission.ALLOWED,
                source="task_run.policy_snapshot",
                reason_code=snapshot_reason or "action_allowed_by_policy_snapshot",
                capability=capability,
                resource_id=resource_id,
            )
        )

        profile_allowed = action in self._profile_actions(profile)
        facets.append(
            CanonicalPolicyFacet(
                facet="runtime_profile",
                permission=CanonicalPermission.ALLOWED if profile_allowed else CanonicalPermission.DENIED,
                source="runtime_profile",
                reason_code=(
                    "action_allowed_by_profile"
                    if profile_allowed
                    else f"action_not_allowed_by_profile:{action}"
                ),
                capability=capability,
                resource_id=resource_id,
            )
        )

        policy_requires_human = action in approvals_required
        if policy_requires_human:
            facets.append(
                CanonicalPolicyFacet(
                    facet="policy_approval_requirement",
                    permission=CanonicalPermission.ASK,
                    source="task_run.policy_snapshot",
                    reason_code="approval_required",
                    capability=capability,
                    resource_id=resource_id,
                    requires_human_authority=True,
                )
            )
        needs_human = resource_requires_human or policy_requires_human
        if needs_human:
            mission_allowed = self._mission_authority_allows(
                run,
                action=capability,
                path=run.workspace,
                resource_id=authority_resource_id or resource_id,
                repository_identity=repository_identity,
                branch=git_branch,
            )
            if mission_allowed:
                facets.append(
                    CanonicalPolicyFacet(
                        facet="human_authority",
                        permission=CanonicalPermission.ALLOWED,
                        source="mission_authority_grant",
                        reason_code="grant_effective",
                        capability=capability,
                        resource_id=authority_resource_id or resource_id,
                        details={"repository_identity": repository_identity, "branch": git_branch},
                    )
                )
            elif existing_approval is not None and existing_approval.status == "approved":
                facets.append(
                    CanonicalPolicyFacet(
                        facet="human_authority",
                        permission=CanonicalPermission.ALLOWED,
                        source="approval_service",
                        reason_code="approval_effective",
                        capability=capability,
                        resource_id=resource_id,
                    )
                )
            elif existing_approval is not None and existing_approval.status not in {"pending", "approved"}:
                facets.append(
                    CanonicalPolicyFacet(
                        facet="human_authority",
                        permission=CanonicalPermission.DENIED,
                        source="approval_service",
                        reason_code="approval_denied",
                        capability=capability,
                        resource_id=resource_id,
                    )
                )

        shell_plan = run.intent_map.get("shell_plan") if isinstance(run.intent_map, dict) else None
        shell_category = str(shell_plan.get("shell_category") or "") if isinstance(shell_plan, dict) else ""
        if action == "run_command" and shell_category in {"git_write_shell", "network_shell", "git_destructive_shell"}:
            facets.append(
                CanonicalPolicyFacet(
                    facet="global_policy",
                    permission=CanonicalPermission.DENIED,
                    source="m5_ambiguous_external_shell_boundary",
                    reason_code=(
                        "git_write_requires_granular_classification"
                        if shell_category == "git_write_shell"
                        else "git_destructive_operation_denied"
                        if shell_category == "git_destructive_shell"
                        else "network_shell_requires_granular_classification"
                    ),
                    capability=capability,
                    resource_id=resource_id,
                    details={"shell_category": shell_category},
                )
            )

        denied_capabilities = set(run.policy_snapshot.get("denied_capabilities", []) or [])
        if capability in denied_capabilities:
            facets.append(
                CanonicalPolicyFacet(
                    facet="capability_policy",
                    permission=CanonicalPermission.DENIED,
                    source="task_run.policy_snapshot",
                    reason_code=f"capability_denied:{capability}",
                    capability=capability,
                    resource_id=resource_id,
                )
            )
        contract = CanonicalOperationContract(
            session_id=run.session_id,
            source_channel=str(run.intent_map.get("source_channel") if isinstance(run.intent_map, dict) and run.intent_map.get("source_channel") else "task_runtime"),
            intent_type=str((run.intent_map.get("intent_type") if isinstance(run.intent_map, dict) else None) or run.operation_type or action),
            operation_type=str(run.operation_type or action),
            contract_type=str(run.contract_type or run.operation_type or action),
            runtime_profile=str(run.runtime_profile or "conversation"),
            requires_task=True,
            requested_actions=[action],
            workspace_path=run.workspace,
        )
        return self.effective_policy.resolve_facets(
            contract,
            facets=facets,
            capability=capability,
            resource_id=resource_id,
        )

    def _legacy_reason_from_canonical(
        self,
        decision: CanonicalPolicyDecision,
        *,
        action: str,
    ) -> str | None:
        if decision.permission == CanonicalPermission.ALLOWED:
            return None
        if decision.permission == CanonicalPermission.ASK:
            return "approval_required"
        for facet in decision.facets:
            if facet.permission in {
                CanonicalPermission.DENIED,
                CanonicalPermission.INVALID,
                CanonicalPermission.EXPIRED,
                CanonicalPermission.STALE,
                CanonicalPermission.NEEDS_CLARIFICATION,
            } and facet.reason_code:
                return str(facet.reason_code)
        return f"canonical_policy_{decision.permission.value}:{action}"

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

    def _decision(
        self,
        reasons: list[str],
        reason: str,
        step_id: str | None = None,
        canonical_policy_decisions: list[CanonicalPolicyDecision] | None = None,
    ) -> TaskRunGuardDecision:
        unique = list(dict.fromkeys(reasons))
        decisions = list(canonical_policy_decisions or [])
        status = "blocked" if unique else "allowed"
        return TaskRunGuardDecision(
            allowed=not unique,
            status=status,
            blocked_reasons=unique,
            canonical_policy_decisions=decisions,
            trace=[
                self.trace_service.item(
                    "task_run_guard",
                    status,
                    reason,
                    step_id=step_id,
                    source="services/runtime/task_run_guard.py",
                    data={
                        "blocked_reasons": unique,
                        "canonical_policy_decisions": [
                            item.model_dump(mode="json") for item in decisions
                        ],
                    },
                )
            ],
        )

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
