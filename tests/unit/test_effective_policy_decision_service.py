from __future__ import annotations

from aipinho.schemas.governance.lifecycle import (
    CanonicalOperationContract,
    CanonicalPermission,
    GovernanceLifecycleReasonCode,
    GovernanceLifecycleState,
)
from aipinho.schemas.policy.effective_policy import EffectivePolicy
from aipinho.schemas.policy.policy_decision import PolicyDecision
from aipinho.services.governance.lifecycle.governance_lifecycle_service import GovernanceLifecycleService
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService


def _legacy_decision(
    status: str,
    *,
    allowed_actions: list[str] | None = None,
    denied_actions: list[str] | None = None,
    approval_required_for: list[str] | None = None,
) -> PolicyDecision:
    return PolicyDecision(
        decision_id=f"policy_{status}",
        status=status,  # type: ignore[arg-type]
        contract_type="filesystem_write",
        allowed_actions=allowed_actions or [],
        denied_actions=denied_actions or [],
        approval_required_for=approval_required_for or [],
        effective_policy=EffectivePolicy(
            allowed_actions=allowed_actions or [],
            denied_actions=denied_actions or [],
            approval_required_for=approval_required_for or [],
        ),
        safe_to_execute=False,
        safe_to_preview=status in {"allowed", "needs_approval"},
    )


def test_effective_policy_adapts_legacy_needs_approval_to_canonical_ask() -> None:
    service = EffectivePolicyDecisionService()
    decision = service.from_policy_decision(
        _legacy_decision("needs_approval", approval_required_for=["write_files"]),
    )

    assert decision.permission == CanonicalPermission.ASK
    assert decision.allowed_actions == []
    assert decision.ask_actions == ["write_files"]
    assert decision.requires_approval is True
    assert decision.reason_code == GovernanceLifecycleReasonCode.APPROVAL_REQUIRED


def test_effective_policy_adapts_legacy_denied_to_canonical_denied() -> None:
    service = EffectivePolicyDecisionService()
    decision = service.from_policy_decision(
        _legacy_decision("denied", denied_actions=["apply_patch"]),
    )

    assert decision.permission == CanonicalPermission.DENIED
    assert decision.denied_actions == ["apply_patch"]
    assert decision.reason_code == GovernanceLifecycleReasonCode.POLICY_DENIED


def test_effective_policy_side_effect_defaults_to_approval_not_allowed() -> None:
    service = EffectivePolicyDecisionService()
    contract = CanonicalOperationContract(
        operation_type="run_command",
        contract_type="shell_execution",
        runtime_profile="shell_build_test",
        requested_actions=["run_command"],
    )

    decision = service.resolve(contract)

    assert decision.permission == CanonicalPermission.ASK
    assert decision.allowed_actions == []
    assert decision.ask_actions == ["run_command"]
    assert decision.requires_approval is True


def test_effective_policy_invalid_upstream_vocabulary_blocks() -> None:
    service = EffectivePolicyDecisionService()
    contract = CanonicalOperationContract(operation_type="conversation")

    decision = service.resolve(contract, explicit_decisions=["mystery_permission"])

    assert decision.permission == CanonicalPermission.DENIED
    assert decision.reason_code == GovernanceLifecycleReasonCode.INVALID_OPERATION
    assert decision.allowed_actions == []


def test_lifecycle_invalid_policy_decision_is_blocked_not_resolved() -> None:
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Explique o estado atual.",
        source_channel="unit",
        explicit_policy_decisions=["mystery_permission"],
    )

    assert snapshot.policy.permission == CanonicalPermission.DENIED
    assert snapshot.reason_code == GovernanceLifecycleReasonCode.INVALID_OPERATION
    assert snapshot.state == GovernanceLifecycleState.BLOCKED
