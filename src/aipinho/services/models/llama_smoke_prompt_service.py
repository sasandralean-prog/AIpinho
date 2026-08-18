from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.llama_smoke_test import LlamaSmokePrompt
from aipinho.schemas.models.manual_inference_profile import ManualInferenceProfile
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.generation_config import GenerationConfig
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.utils.yaml_loader import load_yaml_file


class LlamaSmokePromptService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "llama_smoke_test_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def get_prompt(self, prompt_id: str | None) -> LlamaSmokePrompt | None:
        smoke = self.config.get("smoke_test", {}) if isinstance(self.config.get("smoke_test", {}), dict) else {}
        prompts = self.config.get("prompts", {}) if isinstance(self.config.get("prompts", {}), dict) else {}
        resolved_id = prompt_id or smoke.get("default_prompt_id")
        value = prompts.get(resolved_id)
        if not isinstance(value, dict):
            return None
        return LlamaSmokePrompt(
            prompt_id=str(resolved_id),
            text=str(value.get("text", "")),
            expected_contains_any=[str(item) for item in value.get("expected_contains_any", []) or []],
            max_prompt_chars=int(smoke.get("max_prompt_chars", 500) or 500),
        )

    def build_smoke_prompt(self, request: ManualInferenceRequest, profile: ManualInferenceProfile) -> ModelRequest:
        if request.custom_prompt and not self.config.get("smoke_test", {}).get("allow_custom_prompt", False):
            raise ValueError("custom_prompt_disabled")
        prompt = self.get_prompt(request.prompt_id or profile.prompt_id)
        if prompt is None:
            raise ValueError("prompt_not_allowlisted")
        if len(prompt.text) > min(prompt.max_prompt_chars, profile.max_input_chars):
            raise ValueError("prompt_too_long")
        return ModelRequest(
            model_id=request.model_id or profile.model_id,
            provider_id=profile.provider_id,
            messages=[
                PromptMessage(role="system", content="Manual local smoke test. No tools, no files, no network, no memory, no RAG, no patch."),
                PromptMessage(role="user", content=prompt.text),
            ],
            generation_config=GenerationConfig(temperature=profile.temperature, top_p=profile.top_p, max_tokens=min(profile.max_output_tokens, int(self.config.get("smoke_test", {}).get("max_output_tokens", profile.max_output_tokens) or profile.max_output_tokens))),
            output_contract={"contract_type": profile.output_contract_type, "format": "text"},
            safety_envelope={"envelope_id": profile.safety_envelope_id, "rules": ["no_tools", "no_commands", "no_files", "no_network", "no_memory", "no_rag", "no_patch"]},
            metadata={
                "allow_real_inference": request.allow_real_inference,
                "manual_mode": True,
                "operator_confirmed": request.operator_confirmed,
                "profile_id": profile.profile_id,
                "prompt_id": prompt.prompt_id,
                "ctx_size": profile.ctx_size,
                "timeout_seconds": profile.timeout_seconds,
                "max_stdout_chars": int(self.config.get("smoke_test", {}).get("expected_max_output_chars", 5000) or 5000),
                "max_stderr_chars": 2000,
                **request.metadata,
            },
        )

    def validate_expected_output(self, output: str, prompt_id: str | None) -> dict[str, object]:
        prompt = self.get_prompt(prompt_id)
        if prompt is None:
            return {"enabled": True, "passed": False, "expected_contains_any": [], "reason": "prompt_not_found"}
        expected = prompt.expected_contains_any
        passed = any(item in output for item in expected) if expected else bool(output.strip())
        return {"enabled": True, "passed": passed, "expected_contains_any": expected, "reason": None if passed else "expected_text_not_found"}

    def prompt_summary(self, prompt_id: str | None) -> dict[str, object]:
        prompt = self.get_prompt(prompt_id)
        if prompt is None:
            return {"prompt_id": prompt_id, "configured": False}
        return {"prompt_id": prompt.prompt_id, "configured": True, "prompt_chars": len(prompt.text), "expected_contains_any": prompt.expected_contains_any}

    def status(self) -> dict[str, object]:
        smoke = self.config.get("smoke_test", {}) if isinstance(self.config.get("smoke_test", {}), dict) else {}
        return {"status": "ok", "service": "llama_smoke_prompt", "enabled": bool(smoke.get("enabled", False)), "allowed_prompt_ids": smoke.get("allowed_prompt_ids", [])}
