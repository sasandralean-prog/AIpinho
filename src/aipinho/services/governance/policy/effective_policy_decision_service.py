from __future__ import annotations

from aipinho.schemas.governance.lifecycle import (
    CanonicalOperationContract,
    CanonicalPermission,
    CanonicalPolicyDecision,
    GovernanceLifecycleReasonCode,
)
from aipinho.schemas.policy.policy_decision import PolicyDecision, PolicyResolveRequest
from aipinho.schemas.tasks.task_contract import TaskContractPreview
from aipinho.services.governance.policy.canonical_policy_service import CanonicalPolicyService
from aipinho.services.policy_kernel.policy_kernel_service import PolicyKernelService


class EffectivePolicyDecisionService:
    """Canonical authority for runtime permission decisions.

    The legacy Policy Kernel may still produce PolicyDecision objects during the
    migration window. This service is the boundary that adapts those decisions
    into the canonical lifecycle vocabulary.
    """

    def __init__(
        self,
        canonical_policy: CanonicalPolicyService | None = None,
        legacy_policy_kernel: PolicyKernelService | None = None,
    ) -> None:
        self.canonical_policy = canonical_policy or CanonicalPolicyService()
        self.legacy_policy_kernel = legacy_policy_kernel or PolicyKernelService()

    def normalize(self, value: object) -> CanonicalPermission:
        return self.canonical_policy.normalize(value)

    def resolve(
        self,
        contract: CanonicalOperationContract,
        *,
        explicit_decisions: list[object] | None = None,
    ) -> CanonicalPolicyDecision:
        return self.canonical_policy.resolve(contract, explicit_decisions=explicit_decisions).model_copy(
            update={"source": "effective_policy_decision"}
        )

    def from_policy_decision(
        self,
        decision: PolicyDecision,
        *,
        contract: CanonicalOperationContract | None = None,
    ) -> CanonicalPolicyDecision:
        permission = self.normalize(decision.status)
        requested_actions = list(dict.fromkeys(contract.requested_actions if contract else []))
        denied_actions = list(dict.fromkeys(decision.denied_actions or decision.effective_policy.denied_actions))
        allowed_actions = list(dict.fromkeys(decision.allowed_actions or decision.effective_policy.allowed_actions))
        approval_required_for = list(
            dict.fromkeys(decision.approval_required_for or decision.effective_policy.approval_required_for)
        )

        if permission == CanonicalPermission.INVALID:
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.DENIED,
                denied_actions=denied_actions or requested_actions,
                reason_code=GovernanceLifecycleReasonCode.INVALID_OPERATION,
                reason="Legacy policy decision used an invalid status.",
                source="effective_policy_decision",
                trace=self._trace(decision, permission),
            )
        if permission == CanonicalPermission.DENIED:
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.DENIED,
                denied_actions=denied_actions or requested_actions,
                reason_code=GovernanceLifecycleReasonCode.POLICY_DENIED,
                reason="Legacy policy decision denied the operation.",
                source="effective_policy_decision",
                trace=self._trace(decision, permission),
            )
        if permission == CanonicalPermission.NEEDS_CLARIFICATION:
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.NEEDS_CLARIFICATION,
                ask_actions=approval_required_for or requested_actions,
                reason_code=GovernanceLifecycleReasonCode.NEEDS_CLARIFICATION,
                reason="Legacy policy decision requires clarification.",
                source="effective_policy_decision",
                trace=self._trace(decision, permission),
            )
        if permission == CanonicalPermission.ASK:
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.ASK,
                allowed_actions=[],
                ask_actions=approval_required_for or requested_actions,
                requires_approval=True,
                reason_code=GovernanceLifecycleReasonCode.APPROVAL_REQUIRED,
                reason="Legacy policy decision requires approval.",
                source="effective_policy_decision",
                trace=self._trace(decision, permission),
            )
        if permission in {CanonicalPermission.EXPIRED, CanonicalPermission.STALE}:
            reason_code = (
                GovernanceLifecycleReasonCode.APPROVAL_EXPIRED
                if permission == CanonicalPermission.EXPIRED
                else GovernanceLifecycleReasonCode.APPROVAL_STALE
            )
            return CanonicalPolicyDecision(
                permission=CanonicalPermission.DENIED,
                denied_actions=denied_actions or requested_actions,
                reason_code=reason_code,
                reason=f"Legacy policy decision is {permission.value}.",
                source="effective_policy_decision",
                trace=self._trace(decision, permission),
            )
        return CanonicalPolicyDecision(
            permission=CanonicalPermission.ALLOWED,
            allowed_actions=allowed_actions,
            reason_code=GovernanceLifecycleReasonCode.NONE,
            reason="Legacy policy decision allows the operation.",
            source="effective_policy_decision",
            trace=self._trace(decision, permission),
        )

    def contract_from_policy_request(self, request: PolicyResolveRequest) -> CanonicalOperationContract:
        task_type = request.task.task_type if request.task.task_type != "unknown" else request.intent.intent_type
        return CanonicalOperationContract(
            intent_type=request.intent.intent_type,
            operation_type=task_type,
            contract_type=task_type,
            requested_actions=list(request.task.requested_actions),
            workspace_path=request.workspace.path,
            risk_level=request.intent.risk_level,
            trace=[
                {
                    "stage": "effective_policy_request_adapter",
                    "source": "PolicyResolveRequest",
                    "compatibility": "legacy_policy_schema_preserved",
                }
            ],
        )

    def resolve_policy_request(
        self,
        request: PolicyResolveRequest,
    ) -> tuple[PolicyDecision, CanonicalPolicyDecision]:
        decision = self.legacy_policy_kernel.resolve(request)
        canonical = self.from_policy_decision(decision, contract=self.contract_from_policy_request(request))
        return decision, canonical

    def explain_policy_request(self, request: PolicyResolveRequest) -> dict[str, object]:
        explanation = self.legacy_policy_kernel.explain(request)
        decision = explanation["decision"]
        if isinstance(decision, PolicyDecision):
            canonical = self.from_policy_decision(decision, contract=self.contract_from_policy_request(request))
            explanation["canonical_policy"] = canonical.model_dump(mode="json")
            explanation["canonical_source"] = "effective_policy_decision"
        return explanation

    def contract_preview_for_policy_request(self, request: PolicyResolveRequest) -> TaskContractPreview:
        return self.legacy_policy_kernel.contract_preview(request)

    def status(self) -> dict[str, object]:
        data = self.legacy_policy_kernel.status()
        data["canonical_source"] = "effective_policy_decision"
        data["compatibility_backend"] = "policy_kernel"
        return data

    def _trace(self, decision: PolicyDecision, permission: CanonicalPermission) -> list[dict[str, object]]:
        return [
            {
                "stage": "effective_policy_decision",
                "source": "PolicyDecision",
                "decision_id": decision.decision_id,
                "legacy_status": decision.status,
                "canonical_permission": permission.value,
                "safe_to_execute": decision.safe_to_execute,
                "safe_to_preview": decision.safe_to_preview,
            }
        ]
