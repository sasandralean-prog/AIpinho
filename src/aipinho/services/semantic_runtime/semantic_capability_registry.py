from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_model_binding import RoleModelBinding
from aipinho.schemas.semantic_runtime.capability_registry import CapabilityContract, CapabilityModelBinding
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.utils.yaml_loader import load_yaml_file


class SemanticCapabilityRegistry:
    def __init__(
        self,
        config_path: Path | None = None,
        role_binding_service: RoleModelBindingService | None = None,
    ) -> None:
        self.config_path = config_path or PATHS.config_root / "semantic_runtime" / "capability_registry.yaml"
        self.role_binding_service = role_binding_service or RoleModelBindingService()
        self._contracts: dict[str, CapabilityContract] | None = None
        self._role_bindings: dict[str, CapabilityModelBinding] | None = None

    def load(self) -> "SemanticCapabilityRegistry":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        raw_capabilities = data.get("capabilities", {}) if isinstance(data.get("capabilities", {}), dict) else {}
        self._contracts = {
            str(capability_id): CapabilityContract(capability_id=str(capability_id), **value)
            for capability_id, value in raw_capabilities.items()
            if isinstance(value, dict)
        }
        raw_role_bindings = data.get("role_capability_bindings", {}) if isinstance(data.get("role_capability_bindings", {}), dict) else {}
        self._role_bindings = {
            str(role_id): self._binding_from_config(str(role_id), value)
            for role_id, value in raw_role_bindings.items()
            if isinstance(value, dict)
        }
        self._merge_role_model_bindings()
        return self

    @property
    def contracts(self) -> dict[str, CapabilityContract]:
        if self._contracts is None:
            self.load()
        return self._contracts or {}

    @property
    def role_bindings(self) -> dict[str, CapabilityModelBinding]:
        if self._role_bindings is None:
            self.load()
        return self._role_bindings or {}

    def get_contract(self, capability_id: str) -> CapabilityContract | None:
        return self.contracts.get(capability_id)

    def get_role_binding(self, role_id: str) -> CapabilityModelBinding | None:
        binding = self.role_bindings.get(role_id)
        if binding is not None:
            return binding
        resolved = self.role_binding_service.resolve_binding(role_id)
        return self.role_bindings.get(resolved.role_id) if resolved else None

    def infer_capability_for_role(self, role_id: str, role_binding: RoleModelBinding | None = None) -> str:
        configured = self.role_bindings.get(role_id)
        if configured:
            return configured.capability_id
        binding = role_binding or self.role_binding_service.get_binding(role_id)
        if binding is None:
            return role_id
        capability_tokens = set(binding.allowed_capabilities)
        for capability_id, contract in self.contracts.items():
            semantic_tokens = {capability_id, *contract.aliases, *contract.required_model_capabilities}
            if capability_tokens & semantic_tokens:
                return capability_id
        return role_id

    def aliases_for(self, capability_or_alias: str) -> set[str]:
        result = {capability_or_alias}
        for contract in self.contracts.values():
            semantic_tokens = {contract.capability_id, *contract.aliases}
            if capability_or_alias in semantic_tokens:
                result.update(contract.aliases)
                result.update(contract.required_model_capabilities)
                result.add(contract.capability_id)
        return result

    def capability_tokens(self) -> dict[str, set[str]]:
        return {
            capability_id: {capability_id, *contract.aliases, *contract.required_model_capabilities}
            for capability_id, contract in self.contracts.items()
        }

    def status(self) -> dict[str, object]:
        return {
            "status": "ok" if self.contracts else "degraded",
            "service": "semantic_capability_registry",
            "capabilities": sorted(self.contracts),
            "role_bindings": sorted(self.role_bindings),
        }

    def _binding_from_config(self, role_id: str, value: dict[str, Any]) -> CapabilityModelBinding:
        fallback_models = value.get("fallback_models", value.get("fallback", []))
        escalation_models = value.get("escalation_models", value.get("escalation", []))
        if isinstance(fallback_models, str):
            fallback_models = [fallback_models]
        if isinstance(escalation_models, str):
            escalation_models = [escalation_models]
        return CapabilityModelBinding(
            binding_id=f"role:{role_id}",
            role_id=role_id,
            capability_id=str(value.get("capability")),
            enabled=bool(value.get("enabled", True)),
            primary_model=value.get("primary_model") or value.get("primary"),
            fallback_models=[str(item) for item in fallback_models if item],
            escalation_models=[str(item) for item in escalation_models if item],
            output_contract=value.get("output_contract"),
            allowed_model_capabilities=[str(item) for item in value.get("allowed_model_capabilities", []) or []],
            metadata=value.get("metadata", {}) if isinstance(value.get("metadata", {}), dict) else {},
        )

    def _merge_role_model_bindings(self) -> None:
        role_bindings = self._role_bindings or {}
        for role_binding in self.role_binding_service.list_bindings():
            if role_binding.role_id in role_bindings:
                continue
            capability_id = self.infer_capability_for_role(role_binding.role_id, role_binding)
            role_bindings[role_binding.role_id] = CapabilityModelBinding(
                binding_id=f"role:{role_binding.role_id}",
                role_id=role_binding.role_id,
                capability_id=capability_id,
                enabled=role_binding.enabled,
                primary_model=role_binding.primary_model,
                fallback_models=[item for item in [role_binding.fallback_model] if item],
                escalation_models=role_binding.escalation_candidates(),
                output_contract=role_binding.output_contract,
                allowed_model_capabilities=list(role_binding.allowed_capabilities),
                metadata={"source": "role_model_bindings"},
            )
        self._role_bindings = role_bindings
