from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def test_rag_status_sources_retrieve_bundles_and_lookup():
    status = client.get("/api/v1/rag/status")
    assert status.status_code == 200
    assert status.json()["retrieval_enabled"] is True
    assert status.json()["vectorstore_creation_enabled"] is True
    assert status.json()["legacy_vectorstore_enabled"] is False
    assert status.json()["vector_rag_enabled"] is True
    sources = client.get("/api/v1/rag/sources").json()["sources"]
    assert any(source["source_id"] == "legacy_vectorstore" and source["enabled"] is False for source in sources)
    result = client.post("/api/v1/rag/retrieve/reports", json={"query": "validation gate", "explicit": True, "include_trace": True}).json()
    assert result["status"] in {"found", "partial"}
    retrieval_id = result["retrieval_id"]
    assert client.get(f"/api/v1/rag/retrievals/{retrieval_id}").status_code == 200
    assert client.get(f"/api/v1/rag/retrievals/{retrieval_id}/trace").status_code == 200
    assert client.post("/api/v1/rag/context-bundle", json={"retrieval_id": retrieval_id}).status_code == 200
    assert client.post("/api/v1/rag/evidence-bundle", json={"retrieval_id": retrieval_id}).status_code == 200
    assert client.post("/api/v1/rag/validate-citations", json={"citations": result["context_bundle"]["citations"]}).json()["valid"] is True


def test_rag_files_memory_legacy_and_ingest_guards():
    files = client.post("/api/v1/rag/retrieve/files", json={"query": "AIpinho", "workspace": r"C:\Dev\AIpinho", "paths": ["README.md"], "scope": {"scope_type": "workspace", "workspace": r"C:\Dev\AIpinho"}, "explicit": True})
    assert files.status_code == 200
    assert files.json()["status"] in {"found", "partial"}
    legacy = client.post("/api/v1/rag/retrieve", json={"query": "test", "sources": ["legacy_vectorstore"], "explicit": True}).json()
    assert legacy["status"] == "blocked"
    ingest = client.post("/api/v1/rag/ingest", json={"source": "README.md"}).json()
    assert ingest["status"] == "blocked"
    assert ingest["ingested"] is False
