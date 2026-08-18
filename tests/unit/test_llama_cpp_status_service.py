from aipinho.services.models.llama_cpp_status_service import LlamaCppStatusService


def test_llama_cpp_status_service_default_available():
    status = LlamaCppStatusService().status()
    assert status.status == "available"
    assert status.enabled is True
    assert status.real_inference_enabled is True


def test_llama_cpp_status_service_reports_configured_runtime_paths():
    status = LlamaCppStatusService().status()
    assert status.executable_configured is True
    assert status.model_configured is True
    assert "provider_disabled" not in status.default_blocked_reasons
