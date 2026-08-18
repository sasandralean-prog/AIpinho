from aipinho.services.policy_kernel.policy_precedence_service import PolicyPrecedenceService


def test_default_deny_exists_and_is_final():
    service = PolicyPrecedenceService().load()
    order = service.ordered_rules()

    assert "default_deny" in order
    assert order[-1] == "default_deny"


def test_forbidden_root_precedes_role_policy():
    order = PolicyPrecedenceService().load().ordered_rules()

    assert order.index("forbidden_root") < order.index("role_declared_policy")


def test_capability_gate_precedes_role_policy():
    order = PolicyPrecedenceService().load().ordered_rules()

    assert order.index("capability_gate") < order.index("role_declared_policy")


def test_policy_order_is_stable():
    first = PolicyPrecedenceService().load().ordered_rules()
    second = PolicyPrecedenceService().load().ordered_rules()

    assert first == second
