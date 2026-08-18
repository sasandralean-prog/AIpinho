from __future__ import annotations

from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.semantic_runtime.capability_registry import CapabilitySelection
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.semantic_runtime.model_policy_resolver import ModelPolicyResolver
from aipinho.services.semantic_runtime.semantic_capability_registry import SemanticCapabilityRegistry


class CapabilityResolver:
    def __init__(
        self,
        registry: SemanticCapabilityRegistry | None = None,
        model_registry: ModelRegistryService | None = None,
        provider_registry: ProviderRegistryService | None = None,
        role_binding_service: RoleModelBindingService | None = None,
        policy_resolver: ModelPolicyResolver | None = None,
    ) -> None:
        self.model_registry = model_registry or ModelRegistryService()
        self.provider_registry = provider_registry or ProviderRegistryService()
        self.role_binding_service = role_binding_service or RoleModelBindingService()
        self.registry = registry or SemanticCapabilityRegistry(role_binding_service=self.role_binding_service)
        self.policy = policy_resolver or ModelPolicyResolver(model_registry=self.model_registry, provider_registry=self.provider_registry)

    def resolve_for_role(self, role_id: str, *, manual: bool = False, requested_model_id: str | None = None) -> CapabilitySelection:
        binding = self.registry.get_role_binding(role_id)
        if binding is None:
            return CapabilitySelection(status="unavailable", role_id=role_id, blocked_reasons=["capability_binding_missing"])
        return self.resolve(binding.capability_id, role_id=role_id, manual=manual, requested_model_id=requested_model_id)

    def resolve(self, capability_id: str, *, role_id: str | None = None, manual: bool = False, requested_model_id: str | None = None) -> CapabilitySelection:
        contract = self.registry.get_contract(capability_id)
        binding = self.registry.get_role_binding(role_id) if role_id else None
        warnings: list[str] = []
        trace: list[dict[str, object]] = []
        if contract is None:
            return CapabilitySelection(status="unavailable", capability_id=capability_id, role_id=role_id, blocked_reasons=["capability_contract_missing"])
        if not contract.enabled or (binding is not None and not binding.enabled):
            return CapabilitySelection(status="disabled", capability_id=capability_id, role_id=role_id, blocked_reasons=["capability_disabled"])
        if requested_model_id:
            return self._select_model(capability_id, role_id, requested_model_id, "requested", manual=manual, fallback_model_id=None, warnings=warnings, trace=trace)
        primary = binding.primary_model if binding and binding.primary_model else contract.primary_model
        fallbacks = binding.fallback_models if binding and binding.fallback_models else contract.fallback_models
        escalations = binding.escalation_models if binding and binding.escalation_models else contract.escalation_models
        candidates: list[tuple[str, str]] = []
        if manual:
            candidates.extend((model_id, "escalation") for model_id in escalations)
        if primary:
            candidates.append((primary, "primary"))
        candidates.extend((model_id, "fallback") for model_id in fallbacks)
        fallback_model_id = fallbacks[0] if fallbacks else None
        for model_id, source in candidates:
            evaluated = self.policy.evaluate(model_id, manual=manual)
            trace.append({"model_id": model_id, "source": source, "available": bool(evaluated["available"]), "reasons": evaluated["reasons"]})
            if not evaluated["available"]:
                warnings.extend([str(item) for item in evaluated["reasons"]])
                continue
            return CapabilitySelection(
                allowed=True,
                status=source,  # type: ignore[arg-type]
                capability_id=capability_id,
                role_id=role_id,
                selected_model_id=model_id,
                provider_id=str(evaluated["provider_id"]) if evaluated["provider_id"] else None,
                fallback_model_id=fallback_model_id,
                selection_source=source,
                warnings=list(dict.fromkeys(warnings)),
                trace=trace,
            )
        return CapabilitySelection(
            status="unavailable",
            capability_id=capability_id,
            role_id=role_id,
            fallback_model_id=fallback_model_id,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=["capability_model_unavailable"],
            trace=trace,
        )

    def capabilities_match(self, required: list[str], model_capabilities: list[str]) -> bool:
        model = ModelDefinition(model_id="_capability_check", provider_id="stub.local", display_name="Capability Check", capabilities=model_capabilities)
        return self.policy.model_satisfies(model, required, self._accepted_tokens(required))

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "capability_resolver",
            "registry": self.registry.status(),
        }

    def _select_model(
        self,
        capability_id: str,
        role_id: str | None,
        model_id: str,
        source: str,
        *,
        manual: bool,
        fallback_model_id: str | None,
        warnings: list[str],
        trace: list[dict[str, object]],
    ) -> CapabilitySelection:
        evaluated = self.policy.evaluate(model_id, manual=manual)
        trace.append({"model_id": model_id, "source": source, "available": bool(evaluated["available"]), "reasons": evaluated["reasons"]})
        if not evaluated["available"]:
            return CapabilitySelection(
                status="blocked",
                capability_id=capability_id,
                role_id=role_id,
                fallback_model_id=fallback_model_id,
                blocked_reasons=[str(item) for item in evaluated["reasons"]],
                warnings=warnings,
                trace=trace,
            )
        return CapabilitySelection(
            allowed=True,
            status="requested",
            capability_id=capability_id,
            role_id=role_id,
            selected_model_id=model_id,
            provider_id=str(evaluated["provider_id"]) if evaluated["provider_id"] else None,
            fallback_model_id=fallback_model_id,
            selection_source=source,
            warnings=warnings,
            trace=trace,
        )

    def _accepted_tokens(self, required: list[str]) -> dict[str, set[str]]:
        accepted = {capability: self.registry.aliases_for(capability) for capability in required}
        for capability_id, tokens in self.registry.capability_tokens().items():
            for token in tokens:
                accepted.setdefault(token, set()).update(tokens)
                accepted[token].add(capability_id)
        return accepted
