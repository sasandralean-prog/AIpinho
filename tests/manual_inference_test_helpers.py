from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_provider import ModelProvider
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.models.llama_smoke_prompt_service import LlamaSmokePromptService
from aipinho.services.models.llama_smoke_test_service import LlamaSmokeTestService
from aipinho.services.models.local_model_path_service import LocalModelPathService
from aipinho.services.models.manual_inference_gate_service import ManualInferenceGateService
from aipinho.services.models.manual_inference_profile_service import ManualInferenceProfileService
from aipinho.services.models.model_path_validator import ModelPathValidator
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.models.real_inference_run_store import RealInferenceRunStore
from aipinho.services.models.smoke_test_audit_service import SmokeTestAuditService


MODEL_ID = "llama.local.test"
PROVIDER_ID = "llama_cpp.local"
PROFILE_ID = "llama_cpp_smoke"
PROMPT_ID = "smoke_minimal_pt"


def smoke_policy() -> dict[str, Any]:
    return {
        "smoke_test": {
            "enabled": True,
            "default_prompt_id": PROMPT_ID,
            "allowed_prompt_ids": [PROMPT_ID],
            "allow_custom_prompt": False,
            "max_prompt_chars": 500,
            "max_output_tokens": 64,
            "expected_max_output_chars": 5000,
        },
        "prompts": {
            PROMPT_ID: {
                "text": "Responda apenas: OK",
                "expected_contains_any": ["OK", "Ok", "ok"],
            }
        },
    }


def profile_config(enabled: bool = True, allow_chat_auto_use: bool = False) -> dict[str, Any]:
    return {
        "profiles": {
            PROFILE_ID: {
                "enabled": enabled,
                "provider_id": PROVIDER_ID,
                "model_id": MODEL_ID,
                "real_inference": True,
                "manual_only": True,
                "allow_chat_auto_use": allow_chat_auto_use,
                "allow_report_auto_use": False,
                "allow_analysis_auto_use": False,
                "timeout_seconds": 5,
                "max_input_chars": 500,
                "max_output_tokens": 64,
                "ctx_size": 1024,
                "temperature": 0.0,
                "top_p": 1.0,
                "prompt_id": PROMPT_ID,
                "output_contract_type": "local_smoke_test",
                "safety_envelope_id": "local_smoke_test",
            }
        }
    }


def manual_gate_config(enabled: bool = True, allow_smoke_test: bool = True) -> dict[str, Any]:
    return {
        "manual_inference": {
            "enabled": enabled,
            "allow_smoke_test": allow_smoke_test,
            "require_profile_enabled": True,
            "require_request_opt_in": True,
            "require_operator_confirmation": True,
            "require_prompt_id_allowlist": True,
            "require_valid_executable": True,
            "require_valid_model_path": True,
            "require_safety_envelope": True,
            "require_output_contract": True,
        },
        "defaults": {
            "chat_auto_use": False,
            "report_auto_use": False,
            "analysis_auto_use": False,
        },
    }


def real_gate_config(allow_override: bool = True) -> dict[str, Any]:
    return {
        "real_inference": {
            "enabled": False,
            "default_model": "stub.default",
        },
        "manual_profiles": {
            "allow_manual_profile_override": allow_override,
        },
    }


class FakeLlamaProvider:
    def __init__(self, content: str = "OK", status: str = "completed", finish_reason: str = "stop", real_inference: bool = True) -> None:
        self.content = content
        self.status = status
        self.finish_reason = finish_reason
        self.real_inference = real_inference
        self.invoke_calls = 0
        self.preview_calls = 0

    def invoke_preview(self, model_request):
        self.preview_calls += 1
        return {
            "status": "ok",
            "command_preview": ["llama-cli", "--model", "<validated-model>", "--prompt", "<smoke-prompt>"],
            "runtime_estimate": {"timeout_seconds": model_request.metadata.get("timeout_seconds", 5)},
            "warnings": [],
        }

    def invoke(self, model_request):
        self.invoke_calls += 1
        return ModelResponse(
            request_id=model_request.request_id,
            model_id=model_request.model_id,
            provider_id=model_request.provider_id,
            status=self.status,
            content=self.content,
            finish_reason=self.finish_reason,
            real_inference=self.real_inference,
            warnings=[],
            trace=[{"stage": "fake_provider", "status": self.status}],
        )


def controlled_services(tmp_path: Path, provider: FakeLlamaProvider | None = None):
    exe = tmp_path / "llama-cli.exe"
    model = tmp_path / "model.gguf"
    exe.write_text("fake exe", encoding="utf-8")
    model.write_text("fake model", encoding="utf-8")

    profile_service = ManualInferenceProfileService(config=profile_config(enabled=True))
    path_service = LocalModelPathService(
        config={
            "model_roots": {"allowed": [str(tmp_path)], "blocked": []},
            "models": {
                "test_model": {"model_id": MODEL_ID, "path": str(model), "enabled": True}
            },
            "validation": {
                "require_existing_file": True,
                "require_gguf_extension": True,
                "block_forbidden_roots": True,
            },
        }
    )
    validator = ModelPathValidator(path_service)
    model_registry = ModelRegistryService()
    model_registry._models = {
        MODEL_ID: ModelDefinition(
            model_id=MODEL_ID,
            provider_id=PROVIDER_ID,
            display_name="Test Llama",
            enabled=True,
            real_inference=True,
            modality=["text"],
            capabilities=["chat"],
            roles=["speaker"],
            model_path=str(model),
        )
    }
    provider_registry = ProviderRegistryService()
    provider_registry._providers = {
        PROVIDER_ID: ModelProvider(
            provider_id=PROVIDER_ID,
            type="llama_cpp",
            enabled=True,
            real_inference=True,
            executable_path=str(exe),
        )
    }
    gate = ManualInferenceGateService(
        config=manual_gate_config(enabled=True, allow_smoke_test=True),
        real_gate_config=real_gate_config(allow_override=True),
        smoke_policy=smoke_policy(),
        profile_service=profile_service,
        path_service=path_service,
        validator=validator,
        model_registry=model_registry,
        provider_registry=provider_registry,
    )
    run_store = RealInferenceRunStore(
        config={
            "store": {
                "runs_dir": str(tmp_path / "runs"),
                "events_dir": str(tmp_path / "events"),
                "audit_log": str(tmp_path / "audit" / "manual_inference_smoke.jsonl"),
            }
        }
    )
    audit = SmokeTestAuditService(config={"store": {"audit_log": str(tmp_path / "audit" / "manual_inference_smoke.jsonl")}})
    prompt = LlamaSmokePromptService(config=smoke_policy())
    fake_provider = provider or FakeLlamaProvider()
    service = LlamaSmokeTestService(
        profile_service=profile_service,
        gate_service=gate,
        prompt_service=prompt,
        provider=fake_provider,
        audit_service=audit,
        run_store=run_store,
    )
    return service, gate, prompt, run_store, fake_provider

