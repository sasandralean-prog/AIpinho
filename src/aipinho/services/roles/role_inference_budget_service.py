from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_model_binding import RoleInferenceBudget, RoleInferenceRequest, RoleModelBinding
from aipinho.utils.yaml_loader import load_yaml_file


class RoleInferenceBudgetService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "role_inference_budget_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def calculate(self, binding: RoleModelBinding, request: RoleInferenceRequest, *, hardware_class: str | None = None) -> RoleInferenceBudget:
        budget_class = "large_cpu_slow" if hardware_class == "large_cpu_slow" else binding.max_latency_class
        budgets = self.config.get("budgets", {}) if isinstance(self.config.get("budgets", {}), dict) else {}
        raw = budgets.get(budget_class) or budgets.get("medium") or {}
        prompt_chars = len(request.prompt)
        context_chars = len(str(request.context)) if request.context else 0
        warnings: list[str] = []
        exceeded = False
        if prompt_chars > int(raw.get("max_prompt_chars", 12000)):
            warnings.append("prompt_budget_exceeded")
            exceeded = True
        if context_chars > int(raw.get("max_context_chars", 8000)):
            warnings.append("context_budget_exceeded")
            exceeded = True
        return RoleInferenceBudget(
            role_id=binding.role_id,
            budget_class=str(budget_class),
            max_prompt_chars=int(raw.get("max_prompt_chars", 12000)),
            max_context_chars=int(raw.get("max_context_chars", 8000)),
            max_output_tokens=int(raw.get("max_output_tokens", 1024)),
            timeout_seconds=int(raw.get("timeout_seconds", 90)),
            first_token_warning_seconds=int(raw.get("first_token_warning_seconds", 30)),
            prompt_chars=prompt_chars,
            context_chars=context_chars,
            exceeded=exceeded,
            warnings=warnings,
        )

    def status(self) -> dict[str, object]:
        budgets = self.config.get("budgets", {}) if isinstance(self.config.get("budgets", {}), dict) else {}
        return {"status": "ok", "service": "role_inference_budget", "budgets": sorted(budgets)}
