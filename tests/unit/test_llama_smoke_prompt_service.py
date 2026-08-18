from manual_inference_test_helpers import PROFILE_ID, MODEL_ID, PROVIDER_ID, profile_config, smoke_policy
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.services.models.llama_smoke_prompt_service import LlamaSmokePromptService
from aipinho.services.models.manual_inference_profile_service import ManualInferenceProfileService


def _profile():
    return ManualInferenceProfileService(config=profile_config(enabled=True)).get_profile(PROFILE_ID)


def test_llama_smoke_prompt_service_loads_allowlisted_prompt():
    service = LlamaSmokePromptService(config=smoke_policy())
    prompt = service.get_prompt("smoke_minimal_pt")
    assert prompt is not None
    assert "OK" in prompt.expected_contains_any


def test_llama_smoke_prompt_service_rejects_custom_prompt_by_policy():
    service = LlamaSmokePromptService(config=smoke_policy())
    request = ManualInferenceRequest(profile_id=PROFILE_ID, model_id=MODEL_ID, provider_id=PROVIDER_ID, custom_prompt="custom")
    try:
        service.build_smoke_prompt(request, _profile())
        assert False, "custom prompt should be rejected"
    except ValueError as exc:
        assert str(exc) == "custom_prompt_disabled"


def test_llama_smoke_prompt_service_builds_safe_model_request():
    service = LlamaSmokePromptService(config=smoke_policy())
    request = ManualInferenceRequest(profile_id=PROFILE_ID, model_id=MODEL_ID, provider_id=PROVIDER_ID, allow_real_inference=True, operator_confirmed=True)
    model_request = service.build_smoke_prompt(request, _profile())
    assert model_request.model_id == MODEL_ID
    assert model_request.provider_id == PROVIDER_ID
    assert model_request.metadata["manual_mode"] is True
    assert model_request.metadata["max_stdout_chars"] == 5000
    assert model_request.safety_envelope["rules"] == ["no_tools", "no_commands", "no_files", "no_network", "no_memory", "no_rag", "no_patch"]
    assert model_request.generation_config.max_tokens == 64


def test_llama_smoke_prompt_service_validates_expected_output():
    service = LlamaSmokePromptService(config=smoke_policy())
    assert service.validate_expected_output("OK", "smoke_minimal_pt")["passed"] is True
    assert service.validate_expected_output("HELLO", "smoke_minimal_pt")["passed"] is False
