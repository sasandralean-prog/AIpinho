from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_response import ModelResponse, ModelUsage
from aipinho.schemas.roles.role_model_binding import RoleModelBinding, RoleModelFallback
from aipinho.utils.yaml_loader import load_yaml_file


class RoleModelFallbackService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "role_model_fallback_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def decide(self, binding: RoleModelBinding, *, reason: str) -> RoleModelFallback:
        policy = self.config.get("fallback", {}) if isinstance(self.config.get("fallback", {}), dict) else {}
        fallback_model = binding.fallback_model
        blocked: list[str] = []
        if not policy.get("enabled", True):
            blocked.append("fallback_disabled")
        if fallback_model in set(policy.get("blocked_fallback_models", []) or []):
            blocked.append("fallback_to_manual_only_model_blocked")
        return RoleModelFallback(
            fallback_model_id=fallback_model,
            fallback_allowed=bool(fallback_model and not blocked),
            reason=reason,
            blocked_reasons=blocked,
        )

    def deterministic_response(self, *, request_id: str, role_id: str, fallback_model_id: str | None, reason: str) -> ModelResponse:
        content = f"Deterministic fallback for role {role_id}. Real model output was not accepted. Reason: {reason}. No tools, files, patch, shell, git or network were used."
        return ModelResponse(
            request_id=request_id,
            model_id=fallback_model_id or "deterministic_fallback",
            provider_id="deterministic",
            status="completed",
            content=content,
            usage=ModelUsage(output_chars=len(content), estimated_output_tokens=max(1, len(content) // 4)),
            finish_reason="stop",
            real_inference=False,
            warnings=["deterministic_fallback_used", reason],
            trace=[{"stage": "role_model_fallback", "status": "completed", "reason": reason}],
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_model_fallback"}
