from aipinho.services.rag.vector.llama_server_runtime_service import LlamaServerRuntimeService


def runtime_config() -> dict:
    return {
        "server_defaults": {
            "host": "127.0.0.1",
            "startup_timeout_seconds": 1,
            "request_timeout_seconds": 1,
            "max_input_chars": 8,
            "health_paths": ["/health"],
        },
        "test_runtime": {
            "disable_real_runtime_under_pytest": True,
            "opt_in_env": "AIPINHO_ENABLE_REAL_RAG_RUNTIME_TESTS",
        },
        "embedding": {
            "enabled": True,
            "auto_start": True,
            "provider_id": "llama_cpp_embedding",
            "port": 19191,
            "endpoint_paths": ["/v1/embeddings"],
        },
        "reranker": {
            "enabled": True,
            "auto_start": True,
            "provider_id": "llama_cpp_reranker",
            "port": 19192,
            "endpoint_paths": ["/v1/rerank"],
        },
    }


def test_llama_server_runtime_blocks_real_runtime_under_pytest_without_opt_in(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_runtime_guard")
    monkeypatch.delenv("AIPINHO_ENABLE_REAL_RAG_RUNTIME_TESTS", raising=False)
    service = LlamaServerRuntimeService(config=runtime_config())

    result = service.embed(["hello"], model_id="qwen3_embedding_4b_q5_k_m")

    assert result.status == "error"
    assert "embedding_real_runtime_disabled_in_test_profile" in result.warnings


def test_llama_server_runtime_parses_openai_embedding_payload():
    service = LlamaServerRuntimeService(config=runtime_config())

    vectors = service._extract_embeddings({"data": [{"embedding": [1, 2, 3]}]})

    assert vectors == [[1.0, 2.0, 3.0]]


def test_llama_server_runtime_parses_reranker_payload():
    service = LlamaServerRuntimeService(config=runtime_config())

    scores = service._extract_rerank_scores({"results": [{"index": 1, "relevance_score": 0.7}]}, count=3)

    assert scores == [(1, 0.7)]
