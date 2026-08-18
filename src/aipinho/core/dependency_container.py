from __future__ import annotations

from dataclasses import dataclass

from aipinho.registries.route_registry import RouteRegistry
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.capability_gate_service import CapabilityRegistryService
from aipinho.services.policy_kernel.policy_precedence_service import PolicyPrecedenceService
from aipinho.registries.role_registry import RoleRegistry


@dataclass
class DependencyContainer:
    actions: ActionRegistryService
    capabilities: CapabilityRegistryService
    policy_precedence: PolicyPrecedenceService
    roles: RoleRegistry
    routes: RouteRegistry


def build_container() -> DependencyContainer:
    actions = ActionRegistryService().load()
    capabilities = CapabilityRegistryService().load()
    policy_precedence = PolicyPrecedenceService().load()
    roles = RoleRegistry(action_registry=actions).load()
    routes = RouteRegistry()
    return DependencyContainer(
        actions=actions,
        capabilities=capabilities,
        policy_precedence=policy_precedence,
        roles=roles,
        routes=routes,
    )
