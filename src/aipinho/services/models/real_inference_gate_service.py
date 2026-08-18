from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_path_validation import ModelPathValidation
from aipinho.schemas.models.model_provider import ModelProvider
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.real_inference_gate import RealInferenceGateDecision, RealInferenceGateRequirements
from aipinho.services.models.inference_runtime_limiter import InferenceRuntimeLimiter
from aipinho.utils.yaml_loader import load_yaml_file


class RealInferenceGateService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None, limiter: InferenceRuntimeLimiter | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "real_inference_gate.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.limiter = limiter or InferenceRuntimeLimiter()

    def evaluate(
        self,
        *,
        request: ModelRequest,
        model: ModelDefinition | None,
        provider: ModelProvider | None,
        model_path_validation: ModelPathValidation | None,
        executable_validation: ModelPathValidation | None,
    ) -> RealInferenceGateDecision:
        real_config = self.config.get("real_inference", {}) if isinstance(self.config.get("real_inference", {}), dict) else {}
        routing = self.config.get("routing", {}) if isinstance(self.config.get("routing", {}), dict) else {}
        role_id = str(request.metadata.get("role_id", ""))
        purpose = str(request.metadata.get("purpose", ""))
        manual_opt_in = bool(request.metadata.get("allow_real_inference", False) and request.metadata.get("manual_mode", False))
        auto_conversation_opt_in = (
            bool(routing.get("allow_auto_conversation_inference", False))
            and bool(request.metadata.get("auto_conversation_inference", False))
            and purpose in {str(item) for item in routing.get("auto_conversation_purposes", []) or []}
            and role_id in {str(item) for item in routing.get("auto_conversation_roles", []) or []}
            and not any(bool(request.safety_envelope.get(key, False)) for key in ("tool_calling", "write_files", "patch_apply", "network", "memory_write", "rag_ingest"))
        )
        role_pipeline_opt_in = (
            bool(routing.get("allow_auto_role_pipeline_inference", False))
            and bool(request.metadata.get("role_pipeline_controlled_inference", False) or request.metadata.get("auto_role_pipeline_inference", False))
            and purpose in {str(item) for item in routing.get("auto_role_pipeline_purposes", []) or []}
            and role_id in {str(item) for item in routing.get("auto_role_pipeline_roles", []) or []}
            and not any(bool(request.safety_envelope.get(key, False)) for key in ("tool_calling", "write_files", "patch_apply", "network", "memory_write", "rag_ingest"))
        )
        request_opt_in = manual_opt_in or auto_conversation_opt_in or role_pipeline_opt_in
        input_chars = sum(len(message.content) for message in request.messages)
        budget_check = self.limiter.validate_request(
            input_chars=input_chars,
            output_tokens=request.generation_config.max_tokens,
            has_safety_envelope=bool(request.safety_envelope),
            has_output_contract=bool(request.output_contract),
        )
        requirements = RealInferenceGateRequirements(
            provider_enabled=bool(provider and provider.enabled and provider.real_inference),
            model_enabled=bool(model and model.enabled and model.real_inference),
            model_path_valid=bool(model_path_validation and model_path_validation.valid),
            executable_valid=bool(executable_validation and executable_validation.valid),
            safety_envelope_present=bool(request.safety_envelope),
            output_contract_present=bool(request.output_contract),
            budget_valid=bool(budget_check.get("allowed")),
        )
        blocked: list[str] = []
        warnings: list[str] = [str(item) for item in budget_check.get("warnings", [])]
        real_enabled = bool(real_config.get("enabled", False))
        if not real_enabled:
            blocked.append("real_inference_disabled")
        if real_config.get("require_request_opt_in", True) and not request_opt_in:
            blocked.append("request_opt_in_required")
        if real_config.get("require_provider_enabled", True) and not requirements.provider_enabled:
            blocked.append("provider_disabled_or_not_real_inference")
        if real_config.get("require_model_enabled", True) and not requirements.model_enabled:
            blocked.append("model_disabled_or_not_real_inference")
        if real_config.get("require_model_path_validation", True) and not requirements.model_path_valid:
            blocked.append("model_path_invalid")
        if real_config.get("require_executable_validation", True) and not requirements.executable_valid:
            blocked.append("executable_invalid")
        if real_config.get("require_safety_envelope", True) and not requirements.safety_envelope_present:
            blocked.append("missing_safety_envelope")
        if real_config.get("require_output_contract", True) and not requirements.output_contract_present:
            blocked.append("missing_output_contract")
        if real_config.get("require_prompt_budget", True) and not requirements.budget_valid:
            blocked.extend([str(item) for item in budget_check.get("blocked_reasons", [])])
        blocked = list(dict.fromkeys(blocked))
        allowed = not blocked
        status = "allowed" if allowed else "blocked"
        trace = [
            {"stage": "real_inference_gate", "status": status, "reason": ",".join(blocked) if blocked else "all_requirements_satisfied"},
            {"stage": "requirements", "status": "ok" if allowed else "blocked", "data": {**requirements.model_dump(), "manual_opt_in": manual_opt_in, "auto_conversation_opt_in": auto_conversation_opt_in, "role_pipeline_opt_in": role_pipeline_opt_in}},
        ]
        return RealInferenceGateDecision(
            allowed=allowed,
            status=status,  # type: ignore[arg-type]
            provider_id=provider.provider_id if provider else "llama_cpp.local",
            model_id=model.model_id if model else request.model_id,
            real_inference_enabled=real_enabled,
            request_opt_in=request_opt_in,
            blocked_reasons=blocked,
            warnings=warnings,
            requirements=requirements,
            trace=trace,
        )

    def status(self) -> dict[str, object]:
        real_config = self.config.get("real_inference", {}) if isinstance(self.config.get("real_inference", {}), dict) else {}
        return {"status": "ok", "service": "real_inference_gate", "real_inference_enabled": bool(real_config.get("enabled", False)), "default_model": real_config.get("default_model", "stub.default")}
