from aipinho.services.models.local_model_path_service import LocalModelPathService


def test_local_model_path_service_loads_placeholder_config():
    service = LocalModelPathService()
    models = service.list_models()
    assert any(model.model_id == "llama.local.placeholder" for model in models)
    placeholder = service.get_by_model_id("llama.local.placeholder")
    assert placeholder is not None
    assert placeholder.enabled is False
    assert placeholder.path is None


def test_local_model_path_service_enabled_path_required_warning():
    service = LocalModelPathService(config={"model_roots": {"allowed": [], "blocked": ["C:\\PinhoabacaxiAI"]}, "models": {"x": {"enabled": True, "provider_id": "llama_cpp.local", "model_id": "m", "path": None}}, "validation": {}})
    status = service.status()
    assert status["status"] == "degraded"
    assert status["blocked_roots"] == ["C:\\PinhoabacaxiAI"]
