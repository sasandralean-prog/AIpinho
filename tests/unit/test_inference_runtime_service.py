from __future__ import annotations

from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_provider import ModelProvider
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse, ModelUsage
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.models.inference_runtime_service import InferenceRuntimeService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService


class FakeLlamaAdapter:
    def __init__(self, model_path, executable_path) -> None:
        self.requests = []
        self.model_registry = ModelRegistryService()
        self.model_registry._models = {
            "model.test": ModelDefinition(
                model_id="model.test",
                provider_id="llama_cpp_text",
                display_name="test",
                enabled=True,
                model_path=str(model_path),
            )
        }
        self.provider_registry = ProviderRegistryService()
        self.provider_registry._providers = {
            "llama_cpp_text": ModelProvider(
                provider_id="llama_cpp_text",
                type="llama_cpp_text",
                enabled=True,
                executable_path=str(executable_path),
            )
        }

    def invoke(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            provider_id=request.provider_id,
            status="completed",
            content='{"ok": true}',
            usage=ModelUsage(input_chars=10, output_chars=12),
            real_inference=True,
            metadata={"ctx_size": 2048, "stdout_raw_chars": 12, "stderr_chars": 0, "parser": "fake_json"},
        )

    def invoke_preview(self, request: ModelRequest) -> dict[str, object]:
        return {"status": "ok", "process_started": False}

    def status(self) -> dict[str, object]:
        return {"status": "ok"}


def test_inference_runtime_attaches_deterministic_fingerprint(tmp_path):
    exe = tmp_path / "llama-cli.exe"
    model = tmp_path / "model.gguf"
    exe.write_text("exe", encoding="utf-8")
    model.write_text("model", encoding="utf-8")
    adapter = FakeLlamaAdapter(model, exe)
    runtime = InferenceRuntimeService(llama_cpp=adapter)  # type: ignore[arg-type]
    request = ModelRequest(
        model_id="model.test",
        provider_id="llama_cpp_text",
        messages=[PromptMessage(role="user", content="Return JSON.")],
        output_contract={"contract_type": "json", "format": "json"},
        metadata={"timeout_seconds": 10},
    )

    response = runtime.invoke(request)

    telemetry = response.metadata["inference_runtime"]
    input_artifact = response.metadata["canonical_inference_input_artifact"]
    output_artifact = response.metadata["canonical_inference_output_artifact"]
    input_doctor = response.metadata["inference_input_doctor"]
    fingerprint = telemetry["fingerprint"]
    assert response.status == "completed"
    assert adapter.requests == [request]
    assert fingerprint["executable_path"] == str(exe)
    assert fingerprint["executable_sha256"]
    assert fingerprint["model_path"] == str(model)
    assert fingerprint["model_sha256"]
    assert fingerprint["cwd"] == str(tmp_path)
    assert telemetry["json_valid"] is True
    assert input_artifact["prompt_final"]
    assert output_artifact["replacement_detected"] is False
    assert output_artifact["diagnostics"]
    assert input_doctor["reason_codes"]
    assert response.trace[-1]["stage"] == "inference_runtime"


def test_inference_runtime_explains_legacy_empty_edits(tmp_path):
    exe = tmp_path / "llama-cli.exe"
    model = tmp_path / "model.gguf"
    exe.write_text("exe", encoding="utf-8")
    model.write_text("model", encoding="utf-8")
    adapter = FakeLlamaAdapter(model, exe)

    def empty_edits(request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            provider_id=request.provider_id,
            status="completed",
            content='{"edits": []}',
            usage=ModelUsage(),
            real_inference=True,
            metadata={"ctx_size": 2048, "parser": "fake_json"},
        )

    adapter.invoke = empty_edits  # type: ignore[method-assign]
    response = InferenceRuntimeService(llama_cpp=adapter).invoke(  # type: ignore[arg-type]
        ModelRequest(
            model_id="model.test",
            provider_id="llama_cpp_text",
            messages=[PromptMessage(role="user", content="Return patch JSON.")],
            output_contract={"contract_type": "json", "format": "json"},
        )
    )

    output_artifact = response.metadata["canonical_inference_output_artifact"]
    input_doctor = response.metadata["inference_input_doctor"]
    assert output_artifact["empty_output"] is True
    assert output_artifact["replacement_detected"] is False
    assert "legacy_edits_empty" in output_artifact["diagnostics"]
    assert "PATCH_MODEL_EMPTY_OUTPUT" in input_doctor["reason_codes"]
