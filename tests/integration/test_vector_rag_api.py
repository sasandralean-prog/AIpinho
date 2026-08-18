from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def test_vector_rag_api_status_namespaces_preview_approval_execute_and_query():
    status = client.get("/api/v1/vector-rag/status")
    assert status.status_code == 200
    assert status.json()["legacy_vectorstore_enabled"] is False
    assert status.json()["auto_ingest_enabled"] is False

    namespaces = client.get("/api/v1/vector-rag/namespaces").json()["namespaces"]
    assert any(item["namespace_id"] == "coder_rag" for item in namespaces)

    payload = {
        "namespace_id": "coder_rag",
        "source_type": "source_code_snapshots",
        "source_id": "api_vector_rag_source",
        "text": "API Vector RAG stores cited coder chunks after explicit approval.",
        "source_ref": {
            "source_id": "source_code_snapshots",
            "source_type": "file",
            "ref": "src/aipinho/api.py",
            "location": "src/aipinho/api.py:1-4",
            "content_hash": "b" * 64,
        },
        "citation": {
            "citation_type": "file_line_range",
            "source_ref": {
                "source_id": "source_code_snapshots",
                "source_type": "file",
                "ref": "src/aipinho/api.py",
                "location": "src/aipinho/api.py:1-4",
                "content_hash": "b" * 64,
            },
            "excerpt": "API Vector RAG stores cited coder chunks after explicit approval.",
            "line_start": 1,
            "line_end": 4,
        },
    }
    preview = client.post("/api/v1/vector-rag/ingest-preview", json=payload).json()
    assert preview["status"] == "ready"
    assert preview["would_write_index"] is False

    approval = client.post("/api/v1/vector-rag/ingest-approval", json={"preview_id": preview["preview_id"], "approve": True}).json()
    assert approval["ingested"] is False
    result = client.post("/api/v1/vector-rag/ingest-execute", json={"preview_id": preview["preview_id"], "approval_id": approval["approval"]["approval_id"]}).json()
    assert result["status"] == "indexed"

    query = client.post("/api/v1/vector-rag/query/role/coder", json={"query": "cited coder chunks", "top_k": 3}).json()
    assert query["status"] in {"found", "partial"}
    assert query["hits"]
    assert query["context_bundle"]["citations"]
