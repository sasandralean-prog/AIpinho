from __future__ import annotations

from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_profile import ModelProfile
from aipinho.services.models.model_path_validator import ModelPathValidator
from aipinho.services.models.model_registry_service import ModelRegistryService


class ModelProfileService:
    def __init__(self, registry: ModelRegistryService | None = None, validator: ModelPathValidator | None = None) -> None:
        self.registry = registry or ModelRegistryService()
        self.validator = validator or ModelPathValidator()

    def profile_for_model(self, model: ModelDefinition) -> ModelProfile:
        path_validation = self.validator.validate_model_path(model.model_path, model_enabled=bool(model.model_path))
        return ModelProfile(
            model_id=model.model_id,
            provider_id=model.provider_id,
            display_name=model.display_name,
            hardware_class=model.hardware_class,
            parameter_class=model.parameter_class,
            quantization=model.quantization,
            manual_only=model.manual_only,
            default=model.default,
            default_coding_candidate=model.default_coding_candidate,
            path_configured=bool(model.model_path),
            file_exists=path_validation.exists,
            size_bytes=path_validation.size_bytes,
            capabilities=list(model.capabilities),
            modality=list(model.modality),
            warnings=list(dict.fromkeys([*model.warnings, *path_validation.warnings, *path_validation.blocked_reasons])),
        )

    def get_profile(self, model_id: str) -> ModelProfile | None:
        model = self.registry.get_model(model_id)
        if model is None:
            return None
        return self.profile_for_model(model)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "model_profile"}
