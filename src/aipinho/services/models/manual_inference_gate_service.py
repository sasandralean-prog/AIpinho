from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.manual_inference_profile import ManualInferenceProfile
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.schemas.models.real_inference_gate import RealInferenceGateDecision, RealInferenceGateRequirements
from aipinho.services.models.local_model_path_service import LocalModelPathService
from aipinho.services.models.manual_inference_profile_service import ManualInferenceProfileService
from aipinho.services.models.model_path_validator import ModelPathValidator
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


class ManualInferenceGateService:
    def __init__(
        self,
        config_path: Path | None = None,
        config: dict[str, Any] | None = None,
        real_gate_config: dict[str, Any] | None = None,
        smoke_policy: dict[str, Any] | None = None,
        profile_service: ManualInferenceProfileService | None = None,
        path_service: LocalModelPathService | None = None,
        validator: ModelPathValidator | None = None,
        model_registry: ModelRegistryService | None = None,
        provider_registry: ProviderRegistryService | None = None,
    ) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "manual_inference_gate.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.real_gate_config = real_gate_config or load_yaml_file(PATHS.config_root / "models" / "real_inference_gate.yaml", critical=True, root=PATHS.config_root / "models")
        self.smoke_policy = smoke_policy or load_yaml_file(PATHS.config_root / "models" / "llama_smoke_test_policy.yaml", critical=True, root=PATHS.config_root / "models")
        self.profile_service = profile_service or ManualInferenceProfileService()
        self.path_service = path_service or LocalModelPathService()
        self.validator = validator or ModelPathValidator(self.path_service)
        self.model_registry = model_registry or ModelRegistryService()
        self.provider_registry = provider_registry or ProviderRegistryService()

    def decide(self, request: ManualInferenceRequest, profile: ManualInferenceProfile | None = None) -> RealInferenceGateDecision:
        profile = profile or self.profile_service.get_profile(request.profile_id)
        manual = self.config.get("manual_inference", {}) if isinstance(self.config.get("manual_inference", {}), dict) else {}
        real = self.real_gate_config.get("real_inference", {}) if isinstance(self.real_gate_config.get("real_inference", {}), dict) else {}
        manual_profiles = self.real_gate_config.get("manual_profiles", {}) if isinstance(self.real_gate_config.get("manual_profiles", {}), dict) else {}
        smoke = self.smoke_policy.get("smoke_test", {}) if isinstance(self.smoke_policy.get("smoke_test", {}), dict) else {}
        allowed_prompt_ids = set(smoke.get("allowed_prompt_ids", []) or [])
        blocked: list[str] = []
        warnings: list[str] = []
        if not manual.get("enabled", False):
            blocked.append("manual_inference_disabled")
        if not manual.get("allow_smoke_test", False):
            blocked.append("smoke_test_disabled")
        if profile is None:
            blocked.append("profile_not_found")
        elif manual.get("require_profile_enabled", True) and not profile.enabled:
            blocked.append("profile_disabled")
        if manual.get("require_request_opt_in", True) and not request.allow_real_inference:
            blocked.append("request_opt_in_missing")
        if manual.get("require_operator_confirmation", True) and not request.operator_confirmed:
            blocked.append("operator_confirmation_missing")
        if request.custom_prompt and not smoke.get("allow_custom_prompt", False):
            blocked.append("custom_prompt_disabled")
        prompt_id = request.prompt_id or (profile.prompt_id if profile else smoke.get("default_prompt_id"))
        if manual.get("require_prompt_id_allowlist", True) and prompt_id not in allowed_prompt_ids:
            blocked.append("prompt_not_allowlisted")
        model_id = request.model_id or (profile.model_id if profile else "llama.local.placeholder")
        provider_id = request.provider_id or (profile.provider_id if profile else "llama_cpp.local")
        model = self.model_registry.get_model(model_id)
        provider = self.provider_registry.get_provider(provider_id)
        local_model = self.path_service.get_by_model_id(model_id)
        model_path = request.metadata.get("model_path") or (model.model_path if model and model.model_path else (local_model.path if local_model else None))
        executable_path = request.metadata.get("executable_path") or (provider.executable_path if provider and provider.executable_path else None)
        model_validation = self.validator.validate_model_path(str(model_path) if model_path else None, model_enabled=bool(model and model.enabled))
        executable_validation = self.validator.validate_executable_path(str(executable_path) if executable_path else None, provider_enabled=bool(provider and provider.enabled))
        if manual.get("require_valid_executable", True) and not executable_validation.valid:
            blocked.append("executable_invalid")
        if manual.get("require_valid_model_path", True) and not model_validation.valid:
            blocked.append("model_path_invalid")
        if not provider or not provider.enabled or not provider.real_inference:
            blocked.append("provider_disabled")
        if not model or not model.enabled or not model.real_inference:
            blocked.append("model_disabled")
        if profile:
            if not profile.safety_envelope_id and manual.get("require_safety_envelope", True):
                blocked.append("safety_envelope_missing")
            if not profile.output_contract_type and manual.get("require_output_contract", True):
                blocked.append("output_contract_missing")
            if profile.allow_chat_auto_use or profile.allow_report_auto_use or profile.allow_analysis_auto_use:
                blocked.append("chat_auto_use_forbidden")
        if not real.get("enabled", False):
            if not manual_profiles.get("allow_manual_profile_override", False):
                blocked.append("real_inference_global_disabled")
            else:
                warnings.append("real_inference_global_disabled_manual_override")
        requirements = RealInferenceGateRequirements(
            provider_enabled=bool(provider and provider.enabled and provider.real_inference),
            model_enabled=bool(model and model.enabled and model.real_inference),
            model_path_valid=model_validation.valid,
            executable_valid=executable_validation.valid,
            safety_envelope_present=bool(profile and profile.safety_envelope_id),
            output_contract_present=bool(profile and profile.output_contract_type),
            budget_valid=bool(profile and profile.timeout_seconds > 0 and profile.max_input_chars > 0 and profile.max_output_tokens > 0),
        )
        blocked = list(dict.fromkeys(blocked))
        status = "allowed" if not blocked else "blocked"
        return RealInferenceGateDecision(
            allowed=not blocked,
            status=status,  # type: ignore[arg-type]
            provider_id=provider_id,
            model_id=model_id,
            real_inference_enabled=bool(real.get("enabled", False)),
            request_opt_in=request.allow_real_inference,
            blocked_reasons=blocked,
            warnings=list(dict.fromkeys(warnings)),
            requirements=requirements,
            trace=[
                {"stage": "manual_inference_gate", "status": status, "reason": ",".join(blocked) if blocked else "manual_requirements_satisfied"},
                {"stage": "path_validation", "status": "ok" if model_validation.valid and executable_validation.valid else "blocked", "data": {"model": model_validation.model_dump(), "executable": executable_validation.model_dump()}},
            ],
        )

    def status(self) -> dict[str, object]:
        manual = self.config.get("manual_inference", {}) if isinstance(self.config.get("manual_inference", {}), dict) else {}
        return {"status": "ok", "service": "manual_inference_gate", "manual_inference_enabled": bool(manual.get("enabled", False)), "smoke_test_enabled": bool(manual.get("allow_smoke_test", False))}
