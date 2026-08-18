from aipinho.services.models.model_registry_service import ModelRegistryService


def test_model_registry_lists_stub_and_disabled_placeholder():
    registry = ModelRegistryService()
    models = {model.model_id: model for model in registry.list_models()}
    assert "stub.default" in models
    assert models["stub.default"].enabled is True
    assert models["stub.default"].real_inference is False
    assert "llama.local.placeholder" in models
    assert models["llama.local.placeholder"].enabled is False


def test_model_registry_lists_fourteen_runtime_models_separate_from_compat():
    registry = ModelRegistryService()
    runtime_ids = {model.model_id for model in registry.runtime_models()}
    compat_ids = {model.model_id for model in registry.compat_models()}
    assert len(runtime_ids) == 14
    assert "qwen2_5_coder_7b_q4_k_m" in runtime_ids
    assert "qwen2_5_coder_14b_q5_k_m" in runtime_ids
    assert "stub.default" not in runtime_ids
    assert {"stub.default", "llama.local.placeholder"}.issubset(compat_ids)


def test_model_registry_status_blocks_auto_model_use():
    status = ModelRegistryService().status()
    assert status["registered_local_models"] == 14
    assert status["default_coding_candidate"] == "qwen2_5_coder_7b_q4_k_m"
    assert status["chat_model_use_enabled"] is False
    assert status["role_model_use_enabled"] is False
