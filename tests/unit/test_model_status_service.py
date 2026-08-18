from aipinho.services.models.model_status_service import ModelStatusService


def test_model_status_service_reports_status_only_runtime():
    status = ModelStatusService().status()
    assert status["registered_local_models"] == 14
    assert status["chat_model_use_enabled"] is False
    assert status["role_model_use_enabled"] is True
    assert status["real_inference_enabled"] is True
    assert status["status"] == "ok"
