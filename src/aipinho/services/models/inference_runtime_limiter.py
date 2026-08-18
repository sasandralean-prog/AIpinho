from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.inference_runtime_limits import InferenceRuntimeLimits
from aipinho.utils.yaml_loader import load_yaml_file


class InferenceRuntimeLimiter:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "inference_limits.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def limits(self) -> InferenceRuntimeLimits:
        value = self.config.get("limits", {}) if isinstance(self.config.get("limits", {}), dict) else {}
        return InferenceRuntimeLimits(**value)

    def validate_request(self, *, input_chars: int, output_tokens: int | None, has_safety_envelope: bool, has_output_contract: bool) -> dict[str, object]:
        limits = self.limits()
        blocked: list[str] = []
        warnings: list[str] = []
        if input_chars <= 0 and self.config.get("safety", {}).get("block_empty_prompt", True):
            blocked.append("empty_prompt")
        if input_chars > limits.max_input_chars:
            blocked.append("max_input_chars_exceeded")
        if (output_tokens or limits.default_output_tokens) > limits.max_output_tokens:
            blocked.append("max_output_tokens_exceeded")
        if not has_safety_envelope and self.config.get("safety", {}).get("block_prompt_without_safety_envelope", True):
            blocked.append("missing_safety_envelope")
        if not has_output_contract and self.config.get("safety", {}).get("block_prompt_without_output_contract", True):
            blocked.append("missing_output_contract")
        if limits.timeout_seconds <= 0:
            blocked.append("timeout_required")
        return {"allowed": not blocked, "blocked_reasons": blocked, "warnings": warnings, "limits": limits.model_dump()}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "inference_runtime_limiter", "limits": self.limits().model_dump()}
