from aipinho.schemas.roles.role_policy import RolePolicyRequest
from aipinho.services.roles.effective_role_policy_service import EffectiveRolePolicyService
from aipinho.services.roles.role_contract_service import RoleContractService
from aipinho.services.roles.role_policy_resolver import RolePolicyResolver


def test_all_roles_have_governed_contracts():
    contracts = RoleContractService().list_contracts()
    assert "speaker" in contracts
    assert "semantic_interpreter" in contracts
    assert all(contract.version == "1.0" for contract in contracts.values())


def test_role_permissions_are_clamped_by_contract():
    contract = RoleContractService().get_contract("coder")
    assert contract is not None
    assert contract.permissions.can_call_llm is True
    assert contract.permissions.can_call_tools is False
    assert contract.permissions.can_write is False
    assert contract.restrictions.runtime_execution_forbidden is True


def test_role_policy_resolver_uses_contract_trace():
    result = RolePolicyResolver().resolve(RolePolicyRequest(role_id="speaker", policy_decision={"status": "allowed"}))
    assert result["allowed"] is True
    assert result["trace"][0]["source"] == "role_contract"


def test_effective_role_policy_derives_from_role_contract():
    policy = EffectiveRolePolicyService().resolve(RolePolicyRequest(role_id="speaker", policy_decision={"status": "allowed"}))
    assert policy.allowed is True
    assert policy.can_write is False
    assert policy.can_patch is False
    assert policy.output_contract == "chat_response"
