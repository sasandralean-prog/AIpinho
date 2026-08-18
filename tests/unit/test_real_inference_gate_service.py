from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_provider import ModelProvider
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.models.local_model_path_service import LocalModelPathService
from aipinho.services.models.model_path_validator import ModelPathValidator
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


def test_real_inference_gate_default_disabled_blocks(tmp_path):
    model_path = tmp_path / "model.gguf"
    exe_path = tmp_path / "llama-cli.exe"
    model_path.write_text("m", encoding="utf-8")
    exe_path.write_text("e", encoding="utf-8")
    path_service = LocalModelPathService(config={"model_roots": {"allowed": [str(tmp_path)], "blocked": []}, "models": {}, "validation": {}})
    validator = ModelPathValidator(path_service)
    gate = RealInferenceGateService(config={"real_inference": {"enabled": False}})
    decision = gate.evaluate(
        request=_request(allow_real_inference=True, manual_mode=True),
        model=ModelDefinition(model_id="llama.local.test", provider_id="llama_cpp.local", display_name="test", enabled=True, real_inference=True),
        provider=ModelProvider(provider_id="llama_cpp.local", type="llama_cpp", enabled=True, real_inference=True),
        model_path_validation=validator.validate_model_path(str(model_path), model_enabled=True),
        executable_validation=validator.validate_executable_path(str(exe_path), provider_enabled=True),
    )
    assert decision.allowed is False
    assert "real_inference_disabled" in decision.blocked_reasons


def test_real_inference_gate_requires_request_opt_in(tmp_path):
    model_path = tmp_path / "model.gguf"
    exe_path = tmp_path / "llama-cli.exe"
    model_path.write_text("m", encoding="utf-8")
    exe_path.write_text("e", encoding="utf-8")
    path_service = LocalModelPathService(config={"model_roots": {"allowed": [str(tmp_path)], "blocked": []}, "models": {}, "validation": {}})
    validator = ModelPathValidator(path_service)
    gate = RealInferenceGateService(config={"real_inference": {"enabled": True, "require_request_opt_in": True}})
    decision = gate.evaluate(
        request=_request(),
        model=ModelDefinition(model_id="llama.local.test", provider_id="llama_cpp.local", display_name="test", enabled=True, real_inference=True),
        provider=ModelProvider(provider_id="llama_cpp.local", type="llama_cpp", enabled=True, real_inference=True),
        model_path_validation=validator.validate_model_path(str(model_path), model_enabled=True),
        executable_validation=validator.validate_executable_path(str(exe_path), provider_enabled=True),
    )
    assert decision.allowed is False
    assert "request_opt_in_required" in decision.blocked_reasons


def test_real_inference_gate_allows_only_when_all_requirements_pass(tmp_path):
    model_path = tmp_path / "model.gguf"
    exe_path = tmp_path / "llama-cli.exe"
    model_path.write_text("m", encoding="utf-8")
    exe_path.write_text("e", encoding="utf-8")
    path_service = LocalModelPathService(config={"model_roots": {"allowed": [str(tmp_path)], "blocked": []}, "models": {}, "validation": {}})
    validator = ModelPathValidator(path_service)
    gate = RealInferenceGateService(config={"real_inference": {"enabled": True}})
    decision = gate.evaluate(
        request=_request(allow_real_inference=True, manual_mode=True),
        model=ModelDefinition(model_id="llama.local.test", provider_id="llama_cpp.local", display_name="test", enabled=True, real_inference=True),
        provider=ModelProvider(provider_id="llama_cpp.local", type="llama_cpp", enabled=True, real_inference=True),
        model_path_validation=validator.validate_model_path(str(model_path), model_enabled=True),
        executable_validation=validator.validate_executable_path(str(exe_path), provider_enabled=True),
    )
    assert decision.allowed is True
    assert decision.status == "allowed"


def test_real_inference_gate_allows_safe_auto_conversation(tmp_path):
    model_path = tmp_path / "model.gguf"
    exe_path = tmp_path / "llama-cli.exe"
    model_path.write_text("m", encoding="utf-8")
    exe_path.write_text("e", encoding="utf-8")
    path_service = LocalModelPathService(config={"model_roots": {"allowed": [str(tmp_path)], "blocked": []}, "models": {}, "validation": {}})
    validator = ModelPathValidator(path_service)
    gate = RealInferenceGateService(
        config={
            "real_inference": {"enabled": True, "require_request_opt_in": True},
            "routing": {"allow_auto_conversation_inference": True, "auto_conversation_roles": ["speaker"], "auto_conversation_purposes": ["chat"]},
        }
    )
    decision = gate.evaluate(
        request=_request(auto_conversation_inference=True, purpose="chat", role_id="speaker"),
        model=ModelDefinition(model_id="llama.local.test", provider_id="llama_cpp.local", display_name="test", enabled=True, real_inference=True),
        provider=ModelProvider(provider_id="llama_cpp.local", type="llama_cpp", enabled=True, real_inference=True),
        model_path_validation=validator.validate_model_path(str(model_path), model_enabled=True),
        executable_validation=validator.validate_executable_path(str(exe_path), provider_enabled=True),
    )
    assert decision.allowed is True
    assert decision.request_opt_in is True


def test_real_inference_gate_missing_safety_or_contract_blocks(tmp_path):
    request = ModelRequest(model_id="llama.local.test", provider_id="llama_cpp.local", messages=[PromptMessage(role="user", content="hello")], metadata={"allow_real_inference": True, "manual_mode": True})
    gate = RealInferenceGateService(config={"real_inference": {"enabled": True}})
    decision = gate.evaluate(request=request, model=None, provider=None, model_path_validation=None, executable_validation=None)
    assert "missing_safety_envelope" in decision.blocked_reasons
    assert "missing_output_contract" in decision.blocked_reasons
