from aipinho.services.models.model_load_probe_service import ModelLoadProbeService
from aipinho.services.models.model_registry_service import ModelRegistryService


def test_model_load_probe_is_metadata_only_by_default():
    model = ModelRegistryService().get_runtime_model("qwen2_5_coder_7b_q4_k_m")
    result = ModelLoadProbeService().metadata_probe(model)
    assert result.status == "passed"
    assert result.first_token_probe_executed is False


def test_model_load_probe_blocks_first_token_without_operator_confirmation():
    model = ModelRegistryService().get_runtime_model("qwen2_5_coder_7b_q4_k_m")
    result = ModelLoadProbeService().metadata_probe(model, include_first_token_probe=True, operator_confirmed=False)
    assert result.status == "blocked"
    assert "first_token_probe_requires_operator_confirmation" in result.blocked_reasons
