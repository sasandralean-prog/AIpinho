from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_provider import ModelProvider
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.models.llama_cpp_provider import LlamaCppProvider
from aipinho.services.models.local_model_path_service import LocalModelPathService
from aipinho.services.models.model_path_validator import ModelPathValidator
from aipinho.services.models.model_process_runner import ProcessResult
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.models.real_inference_gate_service import RealInferenceGateService


def _request(**metadata):
    return ModelRequest(
        model_id="llama.local.test",
        provider_id="llama_cpp.local",
        messages=[PromptMessage(role="user", content="hello")],
        output_contract={"contract_type": "plain_text", "format": "text"},
        safety_envelope={"rules": ["no tools"]},
        metadata=metadata,
    )


def _registries(exe_path, *, enabled=True):
    model_registry = ModelRegistryService()
    model_registry._models = {
        "llama.local.test": ModelDefinition(
            model_id="llama.local.test",
            provider_id="llama_cpp.local",
            display_name="test llama",
            enabled=enabled,
            real_inference=True,
            capabilities=["chat"],
            roles=["speaker"],
        )
    }
    provider_registry = ProviderRegistryService()
    provider_registry._providers = {
        "llama_cpp.local": ModelProvider(
            provider_id="llama_cpp.local",
            type="llama_cpp",
            enabled=enabled,
            real_inference=True,
            executable_path=str(exe_path),
        )
    }
    return model_registry, provider_registry


class FakeRunner:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or ProcessResult(status="completed", stdout="model output", stderr="", returncode=0)

    def run(self, argv, *, timeout_seconds, max_stdout_chars, max_stderr_chars, cwd=None, env=None):
        self.calls.append({"argv": argv, "timeout_seconds": timeout_seconds, "cwd": cwd, "env": env})
        return self.result


def _provider(tmp_path, *, gate_enabled=False, registry_enabled=True, runner=None):
    exe = tmp_path / "llama-cli.exe"
    model = tmp_path / "model.gguf"
    exe.write_text("exe", encoding="utf-8")
    model.write_text("model", encoding="utf-8")
    model_registry, provider_registry = _registries(exe, enabled=registry_enabled)
    path_service = LocalModelPathService(config={"model_roots": {"allowed": [str(tmp_path)], "blocked": []}, "models": {"test": {"enabled": registry_enabled, "provider_id": "llama_cpp.local", "model_id": "llama.local.test", "path": str(model), "format": "gguf"}}, "validation": {}})
    validator = ModelPathValidator(path_service)
    gate = RealInferenceGateService(config={"real_inference": {"enabled": gate_enabled}})
    return LlamaCppProvider(model_registry=model_registry, provider_registry=provider_registry, path_service=path_service, validator=validator, gate=gate, runner=runner or FakeRunner())


def test_llama_cpp_provider_blocked_by_gate(tmp_path):
    provider = _provider(tmp_path, gate_enabled=False)
    response = provider.invoke(_request(allow_real_inference=True, manual_mode=True))
    assert response.status == "blocked"
    assert response.real_inference is False
    assert "real_inference_disabled" in response.warnings


def test_llama_cpp_provider_preview_does_not_execute(tmp_path):
    runner = FakeRunner()
    provider = _provider(tmp_path, gate_enabled=False, runner=runner)
    preview = provider.invoke_preview(_request(allow_real_inference=True, manual_mode=True))
    assert preview["process_started"] is False
    assert runner.calls == []
    assert preview["gate_decision"]["allowed"] is False


def test_llama_cpp_provider_disabled_model_no_load(tmp_path):
    runner = FakeRunner()
    provider = _provider(tmp_path, gate_enabled=True, registry_enabled=False, runner=runner)
    response = provider.invoke(_request(allow_real_inference=True, manual_mode=True))
    assert response.status == "blocked"
    assert response.real_inference is False
    assert runner.calls == []


def test_llama_cpp_provider_mocked_allowed_run_marks_real_inference_true(tmp_path):
    runner = FakeRunner()
    provider = _provider(tmp_path, gate_enabled=True, runner=runner)
    response = provider.invoke(_request(allow_real_inference=True, manual_mode=True))
    assert response.status == "completed"
    assert response.content == "model output"
    assert response.real_inference is True
    assert runner.calls


def test_llama_cpp_provider_uses_request_ctx_size(tmp_path):
    runner = FakeRunner()
    provider = _provider(tmp_path, gate_enabled=True, runner=runner)
    provider.invoke(_request(allow_real_inference=True, manual_mode=True, ctx_size=4096))
    argv = runner.calls[0]["argv"]
    assert "--ctx-size" in argv
    assert argv[argv.index("--ctx-size") + 1] == "4096"


def test_llama_cpp_provider_extracts_completion_from_cli_wrapper(tmp_path):
    stdout = "\nLoading model...\n\n> user: hello\n\nmodel output\n\n[ Prompt: 1.0 t/s | Generation: 1.0 t/s ]\n\nExiting...\n"
    runner = FakeRunner(ProcessResult(status="completed", stdout=stdout, stderr="", returncode=0))
    provider = _provider(tmp_path, gate_enabled=True, runner=runner)
    response = provider.invoke(_request(allow_real_inference=True, manual_mode=True))
    assert response.status == "completed"
    assert response.content == "model output"


def test_llama_cpp_provider_strips_reasoning_content(tmp_path):
    stdout = "\nLoading model...\n\n> user: hello\n\n[Start thinking]\ninternal\n[End thinking]\nfinal answer\n\n[ Prompt: 1.0 t/s | Generation: 1.0 t/s ]\n\nExiting...\n"
    runner = FakeRunner(ProcessResult(status="completed", stdout=stdout, stderr="", returncode=0))
    provider = _provider(tmp_path, gate_enabled=True, runner=runner)
    response = provider.invoke(_request(allow_real_inference=True, manual_mode=True))
    assert response.status == "completed"
    assert response.content == "final answer"
    assert "reasoning_content_stripped" in response.warnings


def test_llama_cpp_provider_timeout_response(tmp_path):
    runner = FakeRunner(ProcessResult(status="timeout", stdout="", stderr="timeout", returncode=None, timed_out=True, killed=True))
    provider = _provider(tmp_path, gate_enabled=True, runner=runner)
    response = provider.invoke(_request(allow_real_inference=True, manual_mode=True))
    assert response.status == "error"
    assert response.finish_reason == "timeout"
    assert response.real_inference is True
