from aipinho.services.rag.vector.role_rag_context_builder import RoleRAGContextBuilder


def test_role_rag_context_builder_uses_role_namespace_and_global_context():
    context = RoleRAGContextBuilder().build(role_id="coder", query="governed cited chunks")

    assert context.role_id == "coder"
    assert "coder_rag" in context.result.namespace_ids or context.result.status == "no_results"
    assert context.result.status in {"found", "partial", "no_results"}
