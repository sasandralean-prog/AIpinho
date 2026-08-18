from aipinho.registries.role_registry import RoleRegistry
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.capability_gate_service import CapabilityRegistryService
from aipinho.services.policy_kernel.policy_precedence_service import PolicyPrecedenceService


def test_action_registry_config_is_valid():
    assert ActionRegistryService().load().status()["status"] == "ok"


def test_policy_precedence_config_is_valid():
    assert PolicyPrecedenceService().load().status()["status"] == "ok"


def test_capability_registry_config_is_valid():
    assert CapabilityRegistryService().load().status()["status"] == "ok"


def test_roles_config_is_valid():
    assert RoleRegistry().load().status()["status"] == "ok"
