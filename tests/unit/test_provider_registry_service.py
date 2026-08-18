from aipinho.services.models.provider_registry_service import ProviderRegistryService


def test_provider_registry_keeps_real_providers_disabled():
    registry = ProviderRegistryService()
    providers = {provider.provider_id: provider for provider in registry.list_providers()}
    assert providers["stub.local"].enabled is True
    assert providers["stub.local"].real_inference is False
    assert providers["llama_cpp.local"].enabled is False
    assert providers["transformers.local"].enabled is False


def test_provider_registry_registers_local_gguf_provider_kinds_with_configured_auto_load():
    registry = ProviderRegistryService()
    providers = {provider.provider_id: provider for provider in registry.list_providers()}
    for provider_id in {"llama_cpp_text", "llama_cpp_vision", "llama_cpp_ocr", "llama_cpp_reranker", "llama_cpp_embedding"}:
        assert provider_id in providers
        assert providers[provider_id].supports_tools is False
    assert providers["llama_cpp_text"].auto_load_enabled is True
    assert providers["llama_cpp_embedding"].auto_load_enabled is True
    assert providers["llama_cpp_reranker"].auto_load_enabled is True
    assert providers["llama_cpp_vision"].auto_load_enabled is False
    assert providers["llama_cpp_ocr"].auto_load_enabled is False
