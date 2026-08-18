from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.services.models.manual_inference_gate_service import ManualInferenceGateService
from aipinho.services.models.manual_inference_profile_service import ManualInferenceProfileService
from aipinho.services.models.real_inference_gate_service import RealInferenceGateService
from aipinho.utils.yaml_loader import load_yaml_file


class ChatModelPolicyService:
    def __init__(
        self,
        config_path: Path | None = None,
        config: dict[str, Any] | None = None,
        manual_policy_path: Path | None = None,
        manual_policy: dict[str, Any] | None = None,
        profile_service: ManualInferenceProfileService | None = None,
        manual_gate: ManualInferenceGateService | None = None,
        real_gate: RealInferenceGateService | None = None,
    ) -> None:
        self.config_path = config_path or PATHS.config_root / "chat" / "chat_model_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.manual_policy_path = manual_policy_path or PATHS.config_root / "chat" / "manual_chat_inference_policy.yaml"
        self.manual_policy = manual_policy or load_yaml_file(self.manual_policy_path, critical=True, root=self.manual_policy_path.parent)
        self.profile_service = profile_service or ManualInferenceProfileService()
        self.manual_gate = manual_gate or ManualInferenceGateService(config=self.manual_policy, profile_service=self.profile_service)
        self.real_gate = real_gate or RealInferenceGateService()

    @property
    def normal_chat(self) -> dict[str, Any]:
        value = self.config.get("normal_chat", {})
        return value if isinstance(value, dict) else {}

    @property
    def manual_chat(self) -> dict[str, Any]:
        value = self.config.get("manual_chat", {})
        return value if isinstance(value, dict) else {}

    @property
    def blocked_capabilities(self) -> dict[str, Any]:
        value = self.config.get("blocked_capabilities", {})
        return value if isinstance(value, dict) else {}

    def manual_enabled(self) -> bool:
        return bool(self.manual_chat.get("enabled", False)) and bool((self.manual_policy.get("manual_inference", {}) or {}).get("enabled", False))

    def default_profile_id(self) -> str:
        return str(self.manual_chat.get("default_profile_id", "llama_cpp_manual_small"))

    def normal_chat_model_id(self) -> str:
        return str(self.normal_chat.get("default_model_id") or "").strip()

    def validate_request(self, request: ManualChatInferenceRequest) -> dict[str, Any]:
        reasons: list[str] = []
        warnings: list[str] = []
        if not self.manual_enabled():
            reasons.append("manual_chat_inference_disabled")
        if self.manual_chat.get("require_request_opt_in", True) and not request.allow_real_inference:
            reasons.append("request_opt_in_missing")
        if self.manual_chat.get("require_operator_confirmation", True) and not request.operator_confirmed:
            reasons.append("operator_confirmation_missing")
        allowed_profiles = self.config.get("allowed_profiles", [])
        if isinstance(allowed_profiles, list) and allowed_profiles and request.profile_id not in {str(item) for item in allowed_profiles}:
            reasons.append("profile_not_allowed_for_chat")
        profile = self.profile_service.get_profile(request.profile_id)
        if profile is None:
            reasons.append("profile_not_found")
        elif self.manual_chat.get("require_profile_enabled", True) and not profile.enabled:
            reasons.append("profile_disabled")
        if profile and (profile.allow_chat_auto_use or not profile.manual_only):
            reasons.append("profile_must_be_manual_only")
        manual_request = ManualInferenceRequest(
            profile_id=request.profile_id,
            model_id=request.model_id,
            provider_id=request.provider_id,
            prompt_id=profile.prompt_id if profile else None,
            custom_prompt=None,
            allow_real_inference=request.allow_real_inference,
            operator_confirmed=request.operator_confirmed,
            include_trace=request.include_trace,
            requested_by=request.requested_by,
            metadata={**request.metadata, "source": "chat_manual_inference"},
        )
        manual_gate_decision = self.manual_gate.decide(manual_request, profile)
        if self.manual_chat.get("require_manual_gate", True) and not manual_gate_decision.allowed:
            reasons.extend(manual_gate_decision.blocked_reasons)
        warnings.extend(manual_gate_decision.warnings)
        reasons = list(dict.fromkeys(reasons))
        return {
            "allowed": not reasons,
            "status": "allowed" if not reasons else "blocked",
            "blocked_reasons": reasons,
            "warnings": list(dict.fromkeys(warnings)),
            "profile": profile,
            "manual_gate_decision": manual_gate_decision.model_dump(),
        }

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "chat_model_policy",
            "normal_chat_real_inference": bool(self.normal_chat.get("real_inference_enabled", False)),
            "manual_chat_inference_enabled": self.manual_enabled(),
            "default_model": self.normal_chat_model_id() or None,
            "default_manual_profile": self.default_profile_id(),
            "blocked_capabilities": self.blocked_capabilities,
            "real_inference_gate": self.real_gate.status(),
        }
