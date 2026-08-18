from aipinho.services.rag.retrieval_source_registry import RetrievalSourceRegistry


def test_retrieval_source_registry_lists_enabled_and_blocked_sources():
    registry = RetrievalSourceRegistry()
    ids = {source.source_id for source in registry.list_sources(include_blocked=True)}
    assert {"project_files", "project_reports", "task_results", "validation_results", "patch_apply_results", "curated_memory", "legacy_vectorstore"} <= ids
    assert registry.get_source("legacy_vectorstore").enabled is False
    assert registry.get_source("unknown") is None
