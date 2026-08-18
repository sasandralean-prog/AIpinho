from __future__ import annotations

from aipinho.services.runtime.delegation_decision_engine import DelegationDecisionEngine


def test_delegation_decision_engine_separates_direct_and_delegate():
    engine = DelegationDecisionEngine()

    direct = engine.decide(prompt="2+2", provider="external_model")
    delegated = engine.decide(prompt="Pergunte a AIpinho e acompanhe a task", provider="external_model")

    assert direct.decision == "DIRECT_RESPONSE"
    assert delegated.decision == "DELEGATE"
    assert delegated.requires_delegation_contract is True


def test_side_effect_without_plan_requires_governed_approval_path():
    decision = DelegationDecisionEngine().decide(
        prompt="Rode build e shell neste workspace",
        provider="external_model",
        context={},
    )

    assert decision.decision == "REQUIRES_APPROVAL"
    assert decision.requires_approval is True
