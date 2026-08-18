from aipinho.schemas.rag.vector.contracts import RAGQueryRequest, VectorRAGStatus


def test_vector_rag_contract_defaults_are_governed_and_no_vision_ocr():
    status = VectorRAGStatus()

    assert status.enabled is True
    assert status.legacy_vectorstore_enabled is False
    assert status.auto_ingest_enabled is False
    assert status.embedding_model == "qwen3_embedding_4b_q5_k_m"
    assert status.reranker_model == "qwen3_reranker_4b_q5_k_m"
    assert status.vision_runtime_enabled is False
    assert status.ocr_runtime_enabled is False

    request = RAGQueryRequest(query="hello", role_id="coder")
    assert request.use_global_context is True
