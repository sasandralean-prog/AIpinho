from __future__ import annotations

from aipinho.schemas.models.model_definition import ModelDefinition


class ModelCapabilityDetectorService:
    def detect(self, model: ModelDefinition) -> dict[str, object]:
        return {
            "model_id": model.model_id,
            "provider_id": model.provider_id,
            "capabilities": list(model.capabilities),
            "modality": list(model.modality),
            "detected_from": "config",
        }
