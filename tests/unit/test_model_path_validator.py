from aipinho.services.models.model_path_validator import ModelPathValidator


def test_model_path_validator_accepts_registered_gguf_path():
    validation = ModelPathValidator().validate_model_path(r"C:\Dev\AI\models\Qwen2.5-Coder-7B-Instruct.Q4_K_M.gguf", model_enabled=True)
    assert validation.valid is True
    assert validation.status == "valid"


def test_model_path_validator_blocks_outside_root():
    validation = ModelPathValidator().validate_model_path(r"C:\Temp\model.gguf", model_enabled=True)
    assert validation.valid is False
    assert "outside_allowed_model_roots" in validation.blocked_reasons
