from __future__ import annotations

from aipinho.schemas.governance.lifecycle import (
    CanonicalOperationContract,
    CanonicalPermission,
    CanonicalPolicyDecision,
    GovernanceLifecycleReasonCode,
)


class CanonicalPolicyService:
    """Normalizes every policy vocabulary into the canonical permission enum."""

    ASK_VALUES = {"ask", "needs_approval", "approval_required", "approval_required_for", "waiting_input"}
    DENIED_VALUES = {"denied", "blocked", "forbidden", "not_allowed"}
    ALLOWED_VALUES = {"allowed", "permit", "permitted", "ok"}
    CLARIFICATION_VALUES = {"needs_clarification", "clarification_required", "workspace_required"}
    WRITE_ACTIONS = {
        "write_files",
        "write_file",
        "create_file",
        "modify_file",
        "apply_patch",
        "project_generation",
        "create_directory",
        "run_command",
        "run_tests",
        "delete",
        "delete_file",
        "move",
        "move_file",
        "format",
        "install",
        "build",
        "clean",
        "grant_shell",
        "grant_write",
    }

    def normalize(self, value: object) -> CanonicalPermission:
        text = str(value or "").strip().casefold()
        if text in self.ASK_VALUES:
            return CanonicalPermission.ASK
        if text in self.DENIED_VALUES:
            return CanonicalPermission.DENIED
        if text in self.CLARIFICATION_VALUES:
            return CanonicalPermission.NEEDS_CLARIFICATION
        if text in {"expired"}:
            return CanonicalPermission.EXPIRED
        if text in {"stale", "superseded"}:
            return CanonicalPermission.STALE
        if text in self.ALLOWED_VALUES or not text:
            return CanonicalPermission.ALLOWED
        return CanonicalPermission.INVALID

    def resolve(
        self,
        contract: CanonicalOperationContract,
        *,
        explicit_decisions: list[object] | None = None,
    ) -> CanonicalPolicyDecision:
        decisions = [self.normalize(item) for item in explicit_decisions or []]
        actions = list(dict.fromkeys(contract.requested_actions))
        if any(value == CanonicalPermission.INVALID for value in decisions):
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.DENIED,
                denied_actions=actions,
                reason_code=GovernanceLifecycleReasonCode.INVALID_OPERATION,
                reason="At least one upstream policy decision used an invalid permission vocabulary.",
                trace=[{"stage": "canonical_policy", "input_decisions": [str(item) for item in explicit_decisions or []]}],
            )
        if any(value == CanonicalPermission.EXPIRED for value in decisions):
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.DENIED,
                denied_actions=actions,
                reason_code=GovernanceLifecycleReasonCode.APPROVAL_EXPIRED,
                reason="At least one upstream policy decision is expired.",
                trace=[{"stage": "canonical_policy", "input_decisions": [str(item) for item in explicit_decisions or []]}],
            )
        if any(value == CanonicalPermission.STALE for value in decisions):
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.DENIED,
                denied_actions=actions,
                reason_code=GovernanceLifecycleReasonCode.APPROVAL_STALE,
                reason="At least one upstream policy decision is stale.",
                trace=[{"stage": "canonical_policy", "input_decisions": [str(item) for item in explicit_decisions or []]}],
            )
        if contract.operation_type in {
            "conversation",
            "product_planning_readonly",
            "workspace_permission_list",
            "session_diagnostic",
            "workspace_analysis_readonly",
            "readonly_analysis",
            "workspace_fix_request",
            "capability_truth",
        }:
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.ALLOWED,
                allowed_actions=[],
                reason_code=GovernanceLifecycleReasonCode.READONLY_OR_PLANNING,
                reason="Read-only or non-executing operation.",
            )
        if any(value == CanonicalPermission.DENIED for value in decisions):
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.DENIED,
                denied_actions=actions,
                reason_code=GovernanceLifecycleReasonCode.POLICY_DENIED,
                reason="At least one upstream policy decision denied the operation.",
                trace=[{"stage": "canonical_policy", "input_decisions": [str(item) for item in explicit_decisions or []]}],
            )
        if any(value == CanonicalPermission.NEEDS_CLARIFICATION for value in decisions):
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.NEEDS_CLARIFICATION,
                ask_actions=actions,
                reason_code=GovernanceLifecycleReasonCode.NEEDS_CLARIFICATION,
                reason="The operation needs clarification before preview or execution.",
            )
        if any(value == CanonicalPermission.ASK for value in decisions):
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.ASK,
                ask_actions=actions,
                requires_approval=True,
                reason_code=GovernanceLifecycleReasonCode.APPROVAL_REQUIRED,
                reason="At least one upstream policy decision requires approval.",
            )
        if decisions and all(value == CanonicalPermission.ALLOWED for value in decisions):
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.ALLOWED,
                allowed_actions=actions,
                reason_code=GovernanceLifecycleReasonCode.NONE,
                reason="All upstream policy decisions explicitly allow the operation.",
            )
        if any(action in self.WRITE_ACTIONS for action in actions):
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.ASK,
                ask_actions=actions,
                requires_approval=True,
                reason_code=GovernanceLifecycleReasonCode.APPROVAL_REQUIRED,
                reason="Side-effect operation defaults to approval when no explicit allow is provided.",
            )
        return CanonicalPolicyDecision(
            permission=CanonicalPermission.ALLOWED,
            allowed_actions=actions,
            reason_code=GovernanceLifecycleReasonCode.NONE,
            reason="Operation is allowed by canonical default.",
        )
