from __future__ import annotations

from dataclasses import dataclass, field

from aipinho.schemas.policy.effective_policy import EffectivePolicy
from aipinho.schemas.policy.policy_trace import PolicyTraceItem
from aipinho.schemas.policy.policy_violation import PolicyViolation
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.approval_policy_service import ApprovalPolicyService
from aipinho.services.policy_kernel.capability_gate_service import CapabilityGateResult
from aipinho.services.policy_kernel.policy_context_builder import PolicyContext
from aipinho.services.policy_kernel.policy_trace_service import PolicyTraceService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyResult


@dataclass(frozen=True)
class EffectivePolicyBuildResult:
    policy: EffectivePolicy
    violations: list[PolicyViolation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: list[PolicyTraceItem] = field(default_factory=list)


class EffectivePolicyBuilder:
    def __init__(
        self,
        action_registry: ActionRegistryService | None = None,
        approval_policy: ApprovalPolicyService | None = None,
        trace_service: PolicyTraceService | None = None,
    ) -> None:
        self.action_registry = action_registry or ActionRegistryService().load()
        self.approval_policy = approval_policy or ApprovalPolicyService(action_registry=self.action_registry).load()
        self.trace_service = trace_service or PolicyTraceService()

    def build(
        self,
        *,
        context: PolicyContext,
        workspace: WorkspacePolicyResult,
        capabilities: CapabilityGateResult,
    ) -> EffectivePolicyBuildResult:
        denied: set[str] = set(context.unknown_actions)
        allowed: set[str] = set()
        approval_required: set[str] = set()
        warnings = list(context.warnings)
        violations = list(context.violations) + list(workspace.violations)
        reasons: dict[str, str] = {}
        trace: list[PolicyTraceItem] = []

        for action in context.unknown_actions:
            reasons[action] = "unknown_action_default_deny"

        for action in capabilities.denied_actions:
            denied.add(action)
            reasons[action] = capabilities.reasons.get(action, "capability_denied")

        if workspace.blocked:
            for action in context.normalized_actions:
                denied.add(action)
                reasons[action] = "workspace_policy_denied"

        role_forbidden = {self.action_registry.normalize_action(action) for action in context.role.forbidden_actions}
        role_requires_approval = {self.action_registry.normalize_action(action) for action in context.role.requires_approval}

        # Roles are descriptive participants, not permission authorities. They may add
        # trace context and stricter approval hints, but final permission decisions stay
        # with workspace policy, capability gate, task contract, and approval policy.
        role_limited_actions = role_forbidden.intersection(context.normalized_actions)
        for action in sorted(role_limited_actions):
            warnings.append(f"role_declares_action_limited:{action}")
            trace.append(self.trace_service.create(
                stage="role_policy",
                rule="role_cannot_expand_task_permissions",
                decision="observed",
                reason="role_declared_limit_is_not_permission_decision",
                severity="warning",
                source="config/roles/default_roles.yaml",
                input={"action": action, "role_id": context.request.role.role_id},
            ))

        for action in context.normalized_actions:
            if action in denied:
                continue
            if action in role_requires_approval or self.approval_policy.requires_approval(action):
                approval_required.add(action)
                reasons[action] = "approval_required"
                trace.append(self.trace_service.create(
                    stage="approval_policy",
                    rule="side_effects_require_approval",
                    decision="needs_approval",
                    reason="action_requires_approval_before_execution",
                    severity="warning",
                    source="config/policies/approval_policy.yaml",
                    input={"action": action},
                ))
                continue
            allowed.add(action)

        if context.request.task.read_only:
            for action in ("write_files", "apply_patch"):
                if action not in context.normalized_actions and context.request.task.task_type != "conversation":
                    denied.add(action)
                    reasons[action] = "read_only_constraint"

        if context.request.task.task_type == "artifact_generation":
            denied.add("apply_patch")
            reasons.setdefault("apply_patch", "artifact_writer_not_code_patch")

        trace.append(self.trace_service.create(
            stage="effective_policy",
            rule="denied_wins",
            decision="computed",
            reason="effective_policy_is_restrictive_intersection",
            source="services/policy_kernel/effective_policy_builder.py",
            input={
                "allowed_actions": sorted(allowed),
                "denied_actions": sorted(denied),
                "approval_required_for": sorted(approval_required),
            },
        ))

        policy = EffectivePolicy(
            allowed_actions=sorted(allowed),
            denied_actions=sorted(denied),
            approval_required_for=sorted(approval_required),
            granted_capabilities=capabilities.granted_capabilities,
            denied_capabilities=capabilities.denied_capabilities,
            blocked_by=sorted({reason for reason in reasons.values() if reason != "approval_required"}),
            warnings=warnings,
            reasons=reasons,
        )
        return EffectivePolicyBuildResult(policy=policy, violations=violations, warnings=warnings, trace=trace)

