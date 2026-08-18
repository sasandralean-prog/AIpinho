from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest, RoleModelGateDecisionV2
from aipinho.services.models.model_doctor_service import ModelDoctorService
from aipinho.services.models.model_hardware_estimator import ModelHardwareEstimator
from aipinho.services.models.model_health_service import ModelHealthService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.roles.manual_escalation_gate_service import ManualEscalationGateService
from aipinho.services.roles.role_inference_budget_service import RoleInferenceBudgetService
from aipinho.services.roles.role_inference_policy_service import RoleInferencePolicyService
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_model_trace_service import RoleModelTraceService
from aipinho.services.roles.role_registry_service import RoleRegistryService
from aipinho.services.semantic_runtime.capability_resolver import CapabilityResolver
from aipinho.utils.yaml_loader import load_yaml_file


class RoleModelGateServiceV2:
    def __init__(
        self,
        binding_service: RoleModelBindingService | None = None,
        registry: ModelRegistryService | None = None,
        providers: ProviderRegistryService | None = None,
        roles: RoleRegistryService | None = None,
        capability_resolver: CapabilityResolver | None = None,
    ) -> None:
        self.binding_service = binding_service or RoleModelBindingService()
        self.registry = registry or ModelRegistryService()
        self.providers = providers or ProviderRegistryService()
        self.roles = roles or RoleRegistryService()
        self.capability_resolver = capability_resolver or CapabilityResolver(model_registry=self.registry, provider_registry=self.providers, role_binding_service=self.binding_service)
        self.policy = RoleInferencePolicyService()
        self.budget = RoleInferenceBudgetService()
        self.escalation = ManualEscalationGateService()
        self.health = ModelHealthService(registry=self.registry)
        self.doctor = ModelDoctorService(registry=self.registry, providers=self.providers)
        self.hardware = ModelHardwareEstimator()
        self.trace = RoleModelTraceService()
        self.role_model_policy = load_yaml_file(PATHS.config_root / "roles" / "role_model_policy.yaml", critical=True, root=PATHS.config_root / "roles")
        self.prompt_contracts = load_yaml_file(PATHS.config_root / "roles" / "role_prompt_contracts.yaml", critical=True, root=PATHS.config_root / "roles")

    def decide(self, role_id: str, request: RoleInferenceRequest | None = None, *, model_id: str | None = None, manual: bool = False) -> RoleModelGateDecisionV2:
        request = request or RoleInferenceRequest(role_id=role_id)
        binding = self.binding_service.get_binding(role_id)
        disabled = self.binding_service.get_disabled(role_id)
        trace_id = self.trace.create(role_id, summary=f"RoleModelGateV2 started for {role_id}")
        blocked: list[str] = []
        warnings: list[str] = []
        if disabled:
            blocked.append("role_disabled_until_future_sprint")
            warnings.append(disabled.reason)
            return self._decision(role_id, False, "blocked", None, None, None, blocked, warnings, trace_id)
        if binding is None:
            blocked.append("role_model_binding_missing")
            return self._decision(role_id, False, "blocked", None, None, None, blocked, warnings, trace_id)
        if self.roles.get_role(role_id) is None:
            blocked.append("role_not_registered")
        if not binding.enabled:
            blocked.append("role_model_binding_disabled")
        capability_selection = self.capability_resolver.resolve_for_role(role_id, manual=bool(manual or request.manual_escalation), requested_model_id=model_id or request.requested_model_id)
        warnings.extend(capability_selection.warnings)
        if not capability_selection.allowed:
            blocked.extend(capability_selection.blocked_reasons or ["capability_selection_blocked"])
        selected_model_id = capability_selection.selected_model_id
        model = self.registry.get_runtime_model(str(selected_model_id)) if selected_model_id else None
        provider = self.providers.get_provider(model.provider_id) if model else None
        if model is None:
            blocked.append("model_not_registered")
        else:
            if not model.enabled:
                blocked.append("model_disabled")
            if model.manual_only and not manual and not request.manual_escalation:
                blocked.append("manual_only_model_cannot_be_auto_selected")
            if model.model_id in set(self.role_model_policy.get("blocked_auto_models", []) or []) and not manual and not request.manual_escalation:
                blocked.append("blocked_auto_model")
        if provider is None:
            blocked.append("provider_not_registered")
        else:
            if not provider.enabled:
                blocked.append("provider_disabled")
            if provider.provider_id not in self.policy.allowed_runtime_types():
                blocked.append("provider_runtime_not_allowed_by_policy")
            if binding.metadata.get("pipeline_only") and provider.provider_id != "llama_cpp_text":
                blocked.append("provider_runtime_not_text_inference")
        if model and provider and not self._capabilities_match(binding.allowed_capabilities, model.capabilities):
            blocked.append("capability_mismatch")
        health = self.health.health(model.model_id) if model else None
        if health and health.status == "unknown" and model:
            doctor_result = self.doctor.run_for_model(model.model_id)
            health = self.health.health(model.model_id)
            warnings.append("doctor_metadata_run_created_for_gate") if doctor_result else None
        if health and health.status == "blocked":
            blocked.extend(health.blocked_reasons or ["model_health_blocked"])
        if health and health.status == "degraded":
            warnings.extend(health.warnings)
        if health is None and model is not None:
            blocked.append("model_health_unavailable")
        manual_decision = self.escalation.decide(request, model)
        if manual_decision["status"] == "requires_manual_confirmation":
            blocked.extend([str(item) for item in manual_decision["blocked_reasons"]])
        warnings.extend([str(item) for item in manual_decision.get("warnings", [])])
        hardware = self.hardware.estimate(model) if model else None
        budget = self.budget.calculate(binding, request, hardware_class=hardware.hardware_class if hardware else None)
        if budget.exceeded:
            blocked.append("role_inference_budget_exceeded")
            warnings.extend(budget.warnings)
        contracts = self.prompt_contracts.get("contracts", {}) if isinstance(self.prompt_contracts.get("contracts", {}), dict) else {}
        if not binding.output_contract:
            blocked.append("missing_output_contract")
        elif binding.output_contract not in contracts:
            blocked.append("output_contract_not_found")
        blocked = list(dict.fromkeys(blocked))
        warnings = list(dict.fromkeys(warnings))
        if blocked:
            status = "requires_manual_confirmation" if any("confirmation" in item or "manual_escalation" in item for item in blocked) else "blocked"
            return self._decision(role_id, False, status, selected_model_id, provider.provider_id if provider else None, capability_selection.fallback_model_id, blocked, warnings, trace_id, budget=budget.model_dump(), manual_required=bool(model and model.manual_only), capability_id=capability_selection.capability_id, selection_source=capability_selection.selection_source)
        status = "degraded" if warnings else "allowed"
        return self._decision(role_id, True, status, selected_model_id, provider.provider_id if provider else None, capability_selection.fallback_model_id, blocked, warnings, trace_id, budget=budget.model_dump(), manual_used=bool(request.manual_escalation), capability_id=capability_selection.capability_id, selection_source=capability_selection.selection_source)

    def _capabilities_match(self, allowed: list[str], model_capabilities: list[str]) -> bool:
        return self.capability_resolver.capabilities_match(allowed, model_capabilities)

    def _decision(
        self,
        role_id: str,
        allowed: bool,
        status: str,
        selected_model_id: str | None,
        provider_id: str | None,
        fallback_model_id: str | None,
        blocked: list[str],
        warnings: list[str],
        trace_id: str,
        *,
        budget: dict[str, Any] | None = None,
        manual_required: bool = False,
        manual_used: bool = False,
        capability_id: str | None = None,
        selection_source: str | None = None,
    ) -> RoleModelGateDecisionV2:
        self.trace.record(trace_id, role_id=role_id, event_type="role_model_gate_v2", status=status, summary="Role model gate decision", model_id=selected_model_id, data={"capability_id": capability_id, "selection_source": selection_source, "blocked_reasons": blocked, "warnings": warnings, "budget": budget or {}})
        return RoleModelGateDecisionV2(
            allowed=allowed,
            status=status,  # type: ignore[arg-type]
            role_id=role_id,
            capability_id=capability_id,
            selection_source=selection_source,
            selected_model_id=selected_model_id,
            provider_id=provider_id,
            fallback_model_id=fallback_model_id,
            manual_escalation_required=manual_required,
            manual_escalation_used=manual_used,
            budget=budget or {},
            warnings=warnings,
            blocked_reasons=blocked,
            trace_id=trace_id,
            trace=[{"stage": "role_model_gate_v2", "status": status, "capability_id": capability_id, "selection_source": selection_source, "blocked_reasons": blocked, "warnings": warnings}],
        )

    def status(self) -> dict[str, object]:
        coder_selection = self.capability_resolver.resolve_for_role("coder")
        return {"status": "ok", "service": "role_model_gate_v2", "default_coding_model": coder_selection.selected_model_id, "capability_registry": self.capability_resolver.status()}
