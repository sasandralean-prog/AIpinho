from __future__ import annotations

from aipinho.services.models.model_health_service import ModelHealthService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.vision.multimodal_model_doctor import MultimodalModelDoctor
from aipinho.services.vision.vision_model_registry import VisionModelRegistry


class OCRModelGateService:
    def __init__(self) -> None:
        self.registry = ModelRegistryService()
        self.providers = ProviderRegistryService()
        self.vision_registry = VisionModelRegistry(self.registry)
        self.health = ModelHealthService(registry=self.registry)
        self.doctor = MultimodalModelDoctor()

    def decide(self, model_id: str | None = None) -> dict[str, object]:
        selected = model_id or self.vision_registry.ocr_model_id()
        blocked: list[str] = []
        warnings: list[str] = []
        model = self.registry.get_runtime_model(selected)
        provider = self.providers.get_provider(model.provider_id) if model else None
        if model is None:
            blocked.append("model_not_registered")
        else:
            if "ocr" not in set(model.capabilities):
                blocked.append("ocr_capability_required")
            if model.provider_id != "llama_cpp_ocr":
                blocked.append("ocr_provider_required")
        if provider is None:
            blocked.append("provider_not_registered")
        elif provider.supports_tools:
            blocked.append("ocr_tool_calling_provider_blocked")
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
        return {"allowed": not blocked, "status": "allowed" if not blocked and not warnings else ("degraded" if not blocked else "blocked"), "model_id": selected, "provider_id": model.provider_id if model else None, "warnings": list(dict.fromkeys(warnings)), "blocked_reasons": list(dict.fromkeys(blocked))}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "ocr_model_gate", "model_id": self.vision_registry.ocr_model_id()}
