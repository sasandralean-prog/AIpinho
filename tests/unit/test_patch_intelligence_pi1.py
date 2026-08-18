import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.patch_intelligence_router import router
from aipinho.schemas.patch_intelligence import PatchKnowledgeEntry, PatchKnowledgeQuery
from aipinho.services.patch_intelligence_service import PatchKnowledgeQueryService, PatchKnowledgeRepository, PatchKnowledgeSerializer


def test_patch_knowledge_base_is_versioned_and_deterministic():
    service = PatchKnowledgeQueryService()

    first = service.list_entries()
    second = service.list_entries()

    assert first.version == "1.0"
    assert first.deterministic is True
    assert first.stores_patch_code is False
    assert [entry.entry_id for entry in first.entries] == [entry.entry_id for entry in second.entries]


def test_patch_knowledge_query_filters_generic_patterns():
    service = PatchKnowledgeQueryService()

    result = service.query(PatchKnowledgeQuery(category="workspace_binding_regression", min_confidence="medium"))

    assert result.count == 1
    assert result.entries[0].category == "workspace_binding_regression"
    assert "workspace" in result.entries[0].root_cause.lower()


def test_patch_knowledge_rejects_absolute_project_paths():
    with pytest.raises(ValueError, match="patch_knowledge_entry_must_not_contain_absolute"):
        PatchKnowledgeEntry(
            category="intent_regression",
            regression="bad absolute path",
            root_cause="uses project path",
            correction_strategy="remove path",
            affected_modules=["semantic_runtime"],
            affected_files=[r"C:\Dev\AIpinho\src\aipinho\bad.py"],
        )


def test_patch_knowledge_serializer_roundtrip():
    repository = PatchKnowledgeRepository()
    serializer = PatchKnowledgeSerializer()

    payload = serializer.to_json(repository.base())
    restored = serializer.from_json(payload)

    assert restored.version == repository.base().version
    assert len(restored.entries) == len(repository.base().entries)


def test_patch_intelligence_router_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    status = client.get("/api/v1/runtime/patch-intelligence/status")
    assert status.status_code == 200
    assert status.json()["stores_patch_code"] is False

    listing = client.get("/api/v1/runtime/patch-intelligence/knowledge")
    assert listing.status_code == 200
    first_id = listing.json()["entries"][0]["entry_id"]

    detail = client.get(f"/api/v1/runtime/patch-intelligence/knowledge/{first_id}")
    assert detail.status_code == 200
    assert detail.json()["entry_id"] == first_id

    query = client.post("/api/v1/runtime/patch-intelligence/query", json={"module": "runtime", "limit": 3})
    assert query.status_code == 200
    assert query.json()["count"] >= 1
