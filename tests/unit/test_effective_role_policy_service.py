from aipinho.schemas.roles.role_policy import RolePolicyRequest
from aipinho.services.roles.effective_role_policy_service import EffectiveRolePolicyService


def test_effective_role_policy_analyst_readonly_allowed_without_tools():
    policy = EffectiveRolePolicyService().resolve(RolePolicyRequest(role_id="analyst", policy_decision={"status": "allowed", "allowed_actions": ["read_files"], "denied_actions": ["write_files"]}))
    assert policy.allowed is True
    assert policy.can_call_model is True
    assert policy.can_call_tools is False
    assert policy.can_write is False
    assert policy.can_patch is False
    assert policy.output_contract == "json_findings"


def test_effective_role_policy_speaker_write_denied():
    policy = EffectiveRolePolicyService().resolve(RolePolicyRequest(role_id="speaker", policy_decision={"status": "allowed", "allowed_actions": ["write_files"], "denied_actions": ["write_files"]}, task_contract={"requested_actions": ["write_files"]}))
    assert policy.can_write is False
    assert "write_files" in policy.denied_actions


def test_effective_role_policy_policy_denied_blocks():
    policy = EffectiveRolePolicyService().resolve(RolePolicyRequest(role_id="analyst", policy_decision={"status": "denied"}))
    assert policy.allowed is False
    assert "policy_denied" in policy.blocked_reasons
