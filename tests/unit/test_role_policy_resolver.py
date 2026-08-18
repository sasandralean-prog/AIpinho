from aipinho.schemas.roles.role_policy import RolePolicyRequest
from aipinho.services.roles.role_policy_resolver import RolePolicyResolver


def test_role_policy_resolver_allows_safe_policy():
    result = RolePolicyResolver().resolve(RolePolicyRequest(role_id="speaker", policy_decision={"status": "allowed"}))
    assert result["allowed"] is True


def test_role_policy_resolver_unknown_role_blocks():
    result = RolePolicyResolver().resolve(RolePolicyRequest(role_id="missing", policy_decision={"status": "allowed"}))
    assert result["allowed"] is False
    assert "unknown_role" in result["blocked_reasons"]


def test_role_policy_resolver_policy_denied_blocks():
    result = RolePolicyResolver().resolve(RolePolicyRequest(role_id="analyst", policy_decision={"status": "denied"}))
    assert result["allowed"] is False
    assert "policy_denied" in result["blocked_reasons"]
