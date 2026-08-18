from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry


def test_vector_index_registry_exposes_governed_namespaces_and_blocks_legacy_paths():
    registry = VectorIndexRegistry()

    namespace_ids = {namespace.namespace_id for namespace in registry.list_namespaces()}

    assert "global_ecosystem" in namespace_ids
    assert "coder_rag" in namespace_ids
    assert registry.get_namespace("vision_rag").enabled is True
    assert registry.get_namespace("ocr_rag").enabled is True
    assert registry.is_legacy_path("data/vectorstores/legacy/store") is True
    assert registry.governed_root().as_posix().endswith("data/vectorstores/governed")
