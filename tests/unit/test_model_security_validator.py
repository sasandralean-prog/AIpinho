from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.model_security_validator import ModelSecurityValidator


def test_model_security_validator_accepts_allowed_root():
    model = ModelRegistryService().get_runtime_model("qwen2_5_coder_7b_q4_k_m")
    validation = ModelSecurityValidator().validate(model)
    assert validation.status == "passed"
    assert validation.allowed_root is True


def test_model_security_validator_blocks_network_path():
    model = ModelRegistryService().get_runtime_model("qwen2_5_coder_7b_q4_k_m").model_copy(update={"model_path": r"\\server\share\model.gguf"})
    validation = ModelSecurityValidator().validate(model)
    assert validation.status == "blocked"
    assert "network_path_blocked" in validation.blocked_reasons
