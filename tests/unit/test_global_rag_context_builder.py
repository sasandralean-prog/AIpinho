from aipinho.services.rag.vector.global_rag_context_builder import GlobalRAGContextBuilder


def test_global_rag_context_builder_stays_in_global_namespace():
    context = GlobalRAGContextBuilder().build(query="AIpinho architecture")

    assert context.supporting_context is True
    assert context.result.namespace_ids == ["global_ecosystem"] or context.result.status == "no_results"
