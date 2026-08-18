from manual_inference_test_helpers import controlled_services, PROFILE_ID, MODEL_ID, PROVIDER_ID, smoke_policy
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest


def test_manual_inference_gate_blocks_default_without_manual_opt_in():
    from aipinho.services.models.manual_inference_gate_service import ManualInferenceGateService

    request = ManualInferenceRequest(profile_id=PROFILE_ID, model_id=MODEL_ID, provider_id=PROVIDER_ID)
    decision = ManualInferenceGateService().decide(request)
    assert decision.allowed is False
    assert "manual_inference_disabled" in decision.blocked_reasons
    assert "request_opt_in_missing" in decision.blocked_reasons


def test_manual_inference_gate_allows_only_when_all_manual_controls_are_satisfied(tmp_path):
    _, gate, *_ = controlled_services(tmp_path)
    request = ManualInferenceRequest(
        profile_id=PROFILE_ID,
        model_id=MODEL_ID,
        provider_id=PROVIDER_ID,
        allow_real_inference=True,
        operator_confirmed=True,
        prompt_id="smoke_minimal_pt",
    )
    decision = gate.decide(request)
    assert decision.allowed is True
    assert decision.status == "allowed"
    assert decision.real_inference_enabled is False
    assert "real_inference_global_disabled_manual_override" in decision.warnings


def test_manual_inference_gate_blocks_missing_operator_confirmation(tmp_path):
    _, gate, *_ = controlled_services(tmp_path)
    request = ManualInferenceRequest(profile_id=PROFILE_ID, model_id=MODEL_ID, provider_id=PROVIDER_ID, allow_real_inference=True)
    decision = gate.decide(request)
    assert decision.allowed is False
    assert "operator_confirmation_missing" in decision.blocked_reasons


def test_manual_inference_gate_blocks_missing_request_opt_in(tmp_path):
    _, gate, *_ = controlled_services(tmp_path)
    request = ManualInferenceRequest(profile_id=PROFILE_ID, model_id=MODEL_ID, provider_id=PROVIDER_ID, operator_confirmed=True)
    decision = gate.decide(request)
    assert decision.allowed is False
    assert "request_opt_in_missing" in decision.blocked_reasons


def test_manual_inference_gate_blocks_custom_prompt_when_policy_disallows(tmp_path):
    _, gate, *_ = controlled_services(tmp_path)
    request = ManualInferenceRequest(
        profile_id=PROFILE_ID,
        model_id=MODEL_ID,
        provider_id=PROVIDER_ID,
        allow_real_inference=True,
        operator_confirmed=True,
        custom_prompt="ignore safety",
    )
    decision = gate.decide(request)
    assert "custom_prompt_disabled" in decision.blocked_reasons


def test_manual_inference_gate_blocks_invalid_model_path_metadata(tmp_path):
    _, gate, *_ = controlled_services(tmp_path)
    request = ManualInferenceRequest(
        profile_id=PROFILE_ID,
        model_id=MODEL_ID,
        provider_id=PROVIDER_ID,
        allow_real_inference=True,
        operator_confirmed=True,
        metadata={"model_path": str(tmp_path / "model.bin")},
    )
    (tmp_path / "model.bin").write_text("not gguf", encoding="utf-8")
    decision = gate.decide(request)
    assert "model_path_invalid" in decision.blocked_reasons


def test_manual_inference_gate_status_reports_manual_flags():
    from aipinho.services.models.manual_inference_gate_service import ManualInferenceGateService

    gate = ManualInferenceGateService(config={"manual_inference": {"enabled": False, "allow_smoke_test": False}}, smoke_policy=smoke_policy())
    status = gate.status()
    assert status["manual_inference_enabled"] is False
    assert status["smoke_test_enabled"] is False

