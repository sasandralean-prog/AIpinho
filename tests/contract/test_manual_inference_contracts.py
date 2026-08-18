from aipinho.schemas.models.llama_smoke_test import LlamaSmokePrompt
from aipinho.schemas.models.manual_inference_profile import ManualInferenceProfile
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.schemas.models.manual_inference_result import ManualInferenceResult
from aipinho.schemas.models.real_inference_run import RealInferenceRun
from aipinho.schemas.models.smoke_test_audit import SmokeTestAuditEvent
from aipinho.schemas.models.smoke_test_status import SmokeTestStatus


def test_manual_inference_request_defaults_are_safe():
    request = ManualInferenceRequest()
    assert request.allow_real_inference is False
    assert request.operator_confirmed is False
    assert request.provider_id == "llama_cpp.local"


def test_manual_inference_profile_defaults_are_manual_only():
    profile = ManualInferenceProfile(profile_id="test")
    assert profile.enabled is False
    assert profile.manual_only is True
    assert profile.allow_chat_auto_use is False
    assert profile.safety_envelope_id == "local_smoke_test"


def test_manual_inference_result_default_never_claims_real_process():
    result = ManualInferenceResult()
    assert result.status == "blocked"
    assert result.real_inference is False
    assert result.process_started is False


def test_smoke_status_contract_contains_manual_flags():
    status = SmokeTestStatus(
        manual_inference_enabled=False,
        smoke_test_enabled=False,
        real_inference_global_enabled=False,
        profiles=[],
        llama_cpp_status={"status": "disabled"},
    )
    dumped = status.model_dump()
    assert dumped["status"] == "disabled"
    assert dumped["manual_inference_enabled"] is False
    assert dumped["smoke_test_enabled"] is False


def test_audit_and_run_contracts_do_not_require_raw_prompt():
    audit = SmokeTestAuditEvent(run_id="run_1", profile_id="profile", provider_id="provider", model_id="model", status="blocked")
    run = RealInferenceRun(run_id="run_1", profile_id="profile", provider_id="provider", model_id="model", status="blocked")
    assert "prompt" not in audit.model_dump()
    assert "prompt" not in run.model_dump()


def test_smoke_prompt_contract_tracks_expected_output_without_command_fields():
    prompt = LlamaSmokePrompt(prompt_id="smoke", text="Responda OK", expected_contains_any=["OK"])
    dumped = prompt.model_dump()
    assert dumped["prompt_id"] == "smoke"
    assert "command" not in dumped
