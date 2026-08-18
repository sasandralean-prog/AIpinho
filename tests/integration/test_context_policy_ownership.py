from aipinho.services.policy.decision_ownership_service import DecisionOwnershipService

def test_context_policy_ownership():
    owners=DecisionOwnershipService().matrix().owners
    assert any(o.decision=='context_admission' and o.owner=='context_kernel' for o in owners)
