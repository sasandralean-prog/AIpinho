from manual_inference_test_helpers import FakeLlamaProvider, PROFILE_ID, MODEL_ID, PROVIDER_ID, controlled_services
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.services.models.llama_smoke_test_service import LlamaSmokeTestService


def _request(**overrides):
    data = {"profile_id": PROFILE_ID, "model_id": MODEL_ID, "provider_id": PROVIDER_ID, "allow_real_inference": True, "operator_confirmed": True, "include_trace": True}
    data.update(overrides)
    return ManualInferenceRequest(**data)


def test_llama_smoke_test_service_blocks_default_without_starting_process():
    result = LlamaSmokeTestService().smoke_test(ManualInferenceRequest(profile_id=PROFILE_ID))
    assert result.status == "blocked"
    assert result.process_started is False
    assert result.real_inference is False
    assert result.audit_event_id is not None


def test_llama_smoke_test_service_completes_with_fake_provider(tmp_path):
    service, _, _, _, provider = controlled_services(tmp_path, FakeLlamaProvider(content="OK"))
    result = service.smoke_test(_request())
    assert result.status == "completed"
    assert result.real_inference is True
    assert result.process_started is True
    assert result.expected_output_check.passed is True
    assert provider.invoke_calls == 1


def test_llama_smoke_test_service_marks_unexpected_output_warning(tmp_path):
    service, *_ = controlled_services(tmp_path, FakeLlamaProvider(content="HELLO"))
    result = service.smoke_test(_request())
    assert result.status == "completed_with_warning"
    assert result.expected_output_check.passed is False


def test_llama_smoke_test_service_marks_timeout(tmp_path):
    service, *_ = controlled_services(tmp_path, FakeLlamaProvider(content="", status="error", finish_reason="timeout"))
    result = service.smoke_test(_request())
    assert result.status == "timeout"
    assert result.process_started is True


def test_llama_smoke_preview_never_starts_process(tmp_path):
    service, *_ = controlled_services(tmp_path, FakeLlamaProvider(content="OK"))
    preview = service.preview(_request())
    assert preview["process_started"] is False
    assert preview["gate_decision"]["allowed"] is True
    assert preview["command_preview"]
