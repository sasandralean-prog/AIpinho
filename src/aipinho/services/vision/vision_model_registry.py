from __future__ import annotations

from aipinho.schemas.vision.contracts import MultimodalModelProfile
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.vision.config import vision_config


class VisionModelRegistry:
    def __init__(self, registry: ModelRegistryService | None = None) -> None:
        self.registry = registry or ModelRegistryService()
        self.policy = vision_config("vision_policy.yaml")

    def primary_vision_model_id(self) -> str:
        return str(self.policy["models"]["primary_vision_model"])

    def fallback_vision_model_id(self) -> str:
        return str(self.policy["models"]["fallback_vision_model"])

    def ocr_model_id(self) -> str:
        return str(self.policy["models"]["ocr_model"])

    def profile(self, model_id: str) -> MultimodalModelProfile | None:
        model = self.registry.get_runtime_model(model_id)
        if not model:
            return None
        return MultimodalModelProfile(model_id=model.model_id, provider_id=model.provider_id, modality=model.modality, capabilities=model.capabilities, requires_mmproj=model.requires_mmproj, mmproj_path=model.mmproj_path)

    def models(self) -> list[MultimodalModelProfile]:
        ids = [self.primary_vision_model_id(), self.fallback_vision_model_id(), self.ocr_model_id()]
        return [profile for model_id in ids if (profile := self.profile(model_id))]

    def status(self) -> dict[str, object]:
        return {"status": "ok" if len(self.models()) == 3 else "degraded", "service": "vision_model_registry", "models": [item.model_dump() for item in self.models()]}
