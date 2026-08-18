import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.semantic_learning_router import router
from aipinho.schemas.semantic_learning import SemanticConcept, SemanticKnowledgeEntry, SemanticKnowledgeQuery
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation
from aipinho.services.semantic_learning_service import SemanticKnowledgeQueryService, SemanticKnowledgeRepository, SemanticKnowledgeSerializer


def test_semantic_knowledge_base_is_versioned_and_generic():
    service = SemanticKnowledgeQueryService()

    result = service.list_entries()

    assert result.version == "1.0"
    assert result.deterministic is True
    assert result.stores_full_prompt is False
    assert result.stores_project_specific_data is False
    assert result.count >= 3


def test_semantic_knowledge_query_by_intent_and_scope():
    result = SemanticKnowledgeQueryService().query(
        SemanticKnowledgeQuery(canonical_intent="repository_analysis", scope="repository", min_confidence="medium")
    )

    assert result.count == 1
    assert result.entries[0].canonical_intent == "repository_analysis"
    assert result.entries[0].isr.intent == "repository_analysis"


def test_semantic_knowledge_concepts_are_reusable():
    concepts = SemanticKnowledgeQueryService().concepts()

    assert concepts.count >= 3
    assert "repository_analysis" in {concept.canonical_intent for concept in concepts.concepts}


def test_semantic_knowledge_rejects_paths_tokens_and_long_prompt_like_reasoning():
    concept = SemanticConcept(
        concept_id="concept_bad",
        name="Bad",
        canonical_intent="repository_analysis",
        scope="repository",
        description="Bad concept",
    )
    with pytest.raises(ValueError, match="semantic_knowledge_must_not_contain_paths"):
        SemanticKnowledgeEntry(
            concept=concept,
            canonical_intent="repository_analysis",
            scope="repository",
            isr=IntermediateSemanticRepresentation(
                intent="repository_analysis",
                scope="repository",
                constraints={"path": r"C:\Dev\AIpinho"},
                semantic_trace=[{"stage": "test", "status": "ready"}],
            ),
        )


def test_semantic_knowledge_serializer_roundtrip():
    repository = SemanticKnowledgeRepository()
    serializer = SemanticKnowledgeSerializer()

    restored = serializer.from_json(serializer.to_json(repository.base()))

    assert restored.version.version == "1.0"
    assert len(restored.entries) == len(repository.base().entries)


def test_semantic_learning_router_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    status = client.get("/api/v1/runtime/semantic-learning/status")
    assert status.status_code == 200
    assert status.json()["stores_full_prompt"] is False

    knowledge = client.get("/api/v1/runtime/semantic-learning/knowledge")
    assert knowledge.status_code == 200
    assert knowledge.json()["count"] >= 3

    query = client.post("/api/v1/runtime/semantic-learning/query", json={"canonical_intent": "write_patch"})
    assert query.status_code == 200
    assert query.json()["entries"][0]["canonical_intent"] == "write_patch"

    concepts = client.get("/api/v1/runtime/semantic-learning/concepts")
    assert concepts.status_code == 200
    assert concepts.json()["count"] >= 3
