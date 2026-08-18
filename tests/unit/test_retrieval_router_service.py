from aipinho.services.rag.retrieval_router_service import RetrievalRouterService


def test_retrieval_router_maps_known_adapters_and_rejects_unknown():
    router = RetrievalRouterService()
    assert router.adapter_for("file_retrieval_source") is not None
    assert router.adapter_for("project_report_retrieval_source") is not None
    assert router.adapter_for("curated_memory_retrieval_source") is not None
    assert router.adapter_for("unknown_adapter") is None
