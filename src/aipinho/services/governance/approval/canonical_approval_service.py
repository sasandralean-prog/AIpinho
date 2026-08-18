from __future__ import annotations

from aipinho.schemas.governance.lifecycle import (
    CanonicalApprovalGate,
    CanonicalExecutionPlan,
    CanonicalPolicyDecision,
    CanonicalPermission,
    GovernanceLifecycleReasonCode,
    PreviewKind,
)


class CanonicalApprovalService:
    """Owns the approval gate semantics for the canonical lifecycle."""

    def evaluate(self, policy: CanonicalPolicyDecision, plan: CanonicalExecutionPlan) -> CanonicalApprovalGate:
        if policy.permission == CanonicalPermission.DENIED:
            return CanonicalApprovalGate(
                required=False,
                can_create_approval=False,
                status="blocked",
                reason_code=GovernanceLifecycleReasonCode.POLICY_DENIED,
            )
        if policy.permission == CanonicalPermission.NEEDS_CLARIFICATION:
            return CanonicalApprovalGate(
                required=False,
                can_create_approval=False,
                status="needs_clarification",
                reason_code=GovernanceLifecycleReasonCode.NEEDS_CLARIFICATION,
            )
        if policy.permission != CanonicalPermission.ASK:
            return CanonicalApprovalGate(required=False, can_create_approval=False, status="not_required")
        if plan.preview_kind != PreviewKind.EXECUTABLE or not plan.executable or not plan.executable_plan_ref:
            reason = plan.blocked_reason
            if reason == GovernanceLifecycleReasonCode.NONE:
                reason = GovernanceLifecycleReasonCode.MISSING_EXECUTABLE_PLAN
            return CanonicalApprovalGate(
                required=True,
                can_create_approval=False,
                status=self._status_for_reason(reason),
                reason_code=reason,
            )
        return CanonicalApprovalGate(
            required=True,
            can_create_approval=True,
            status="pending_approval",
            reason_code=GovernanceLifecycleReasonCode.APPROVAL_REQUIRED,
        )

    def _status_for_reason(self, reason_code: GovernanceLifecycleReasonCode) -> str:
        if reason_code == GovernanceLifecycleReasonCode.MISSING_EXECUTABLE_PLAN:
            return "approval_not_created_no_executable_plan"
        text = reason_code.value
        if text.startswith("APPROVAL_NOT_CREATED") or text.startswith("WORKSPACE_DISCOVERY"):
            return text
        if text.startswith("PREVIEW_REJECTED"):
            return text
        return "approval_not_created_no_executable_plan"
