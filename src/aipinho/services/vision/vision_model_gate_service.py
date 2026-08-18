from __future__ import annotations

from aipinho.services.models.model_health_service import ModelHealthService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.vision.multimodal_model_doctor import MultimodalModelDoctor
from aipinho.services.vision.vision_model_registry import VisionModelRegistry


class VisionModelGateService:
    def __init__(self) -> None:
        self.registry = ModelRegistryService()
        self.providers = ProviderRegistryService()
        self.vision_registry = VisionModelRegistry(self.registry)
        self.health = ModelHealthService(registry=self.registry)
        self.doctor = MultimodalModelDoctor()

    def decide(self, model_id: str | None = None, *, fallback: bool = False) -> dict[str, object]:
        selected = model_id or (self.vision_registry.fallback_vision_model_id() if fallback else self.vision_registry.primary_vision_model_id())
        blocked: list[str] = []
        warnings: list[str] = []
        model = self.registry.get_runtime_model(selected)
        provider = self.providers.get_provider(model.provider_id) if model else None
        if model is None:
            blocked.append("model_not_registered")
        else:
            if "vision" not in set(model.capabilities):
                blocked.append("vision_capability_required")
            if model.provider_id != "llama_cpp_vision":
                blocked.append("vision_provider_required")
        if provider is None:
            blocked.append("provider_not_registered")
        elif provider.supports_tools:
            blocked.append("vision_tool_calling_provider_blocked")
        if model and model.requires_mmproj:
            mmproj = self.doctor.mmproj.validate(model.model_id)
            if not mmproj.valid:
                blocked.extend(mmproj.blocked_reasons)
        health = self.health.health(selected) if model else None
        if health is None and model:
            doctor_result = self.doctor.doctor(selected)
            warnings.append("model_doctor_metadata_run_created")
            if doctor_result.get("status") == "blocked":
                blocked.extend([str(item) for item in doctor_result.get("blocked_reasons", [])])
            else:
                warnings.extend([str(item) for item in doctor_result.get("warnings", [])])
        elif health and health.status == "blocked":
            blocked.extend(health.blocked_reasons or ["model_health_blocked"])
        elif health and health.status == "degraded":
            warnings.extend(health.warnings)
        return {"allowed": not blocked, "status": "allowed" if not blocked and not warnings else ("degraded" if not blocked else "blocked"), "model_id": selected, "provider_id": model.provider_id if model else None, "warnings": list(dict.fromkeys(warnings)), "blocked_reasons": list(dict.fromkeys(blocked)), "fallback": fallback}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vision_model_gate", "primary": self.vision_registry.primary_vision_model_id(), "fallback": self.vision_registry.fallback_vision_model_id()}
