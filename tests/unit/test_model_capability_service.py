from aipinho.services.models.model_capability_service import ModelCapabilityService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService


def test_model_capability_service_validates_provider_match():
    registry = ModelRegistryService()
    providers = ProviderRegistryService()
    model = registry.get_runtime_model("qwen3_embedding_4b_q5_k_m")
    provider = providers.get_provider(model.provider_id)
    decision = ModelCapabilityService().validate_provider_match(model, provider)
    assert decision["status"] == "passed"


def test_model_capability_service_blocks_wrong_embedding_provider_use():
    registry = ModelRegistryService()
    providers = ProviderRegistryService()
    model = registry.get_runtime_model("qwen2_5_coder_7b_q4_k_m").model_copy(update={"provider_id": "llama_cpp_embedding"})
    provider = providers.get_provider("llama_cpp_embedding")
    decision = ModelCapabilityService().validate_provider_match(model, provider)
    assert decision["status"] == "blocked"
