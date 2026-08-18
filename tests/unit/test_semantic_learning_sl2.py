from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.semantic_learning_router import router
from aipinho.schemas.semantic_learning import SemanticPatternRecognitionRequest
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISREntity
from aipinho.services.semantic_learning_service import SemanticPatternEngine, SemanticPatternNormalizer, SemanticPatternScorer, SemanticKnowledgeRepository


def _isr(intent="repository_analysis", scope="repository"):
    return IntermediateSemanticRepresentation(
        intent=intent,
        scope=scope,
        entities=[ISREntity(entity_type="repository", value="generic_repository", confidence=0.9)],
        constraints={"read_only": True, "workspace_mutation": False},
        expected_outputs=["analysis_report"],
        ambiguity={"score": 0.2, "reasons": ["workspace resolution may be needed"]},
        confidence=0.9,
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )


def test_semantic_pattern_recognition_is_deterministic_and_prompt_free():
    request = SemanticPatternRecognitionRequest(isr=_isr())

    first = SemanticPatternEngine().recognize(request)
    second = SemanticPatternEngine().recognize(request)

    assert first.count >= 1
    assert first.prompt_used is False
    assert first.modifies_runtime is False
    assert [match.pattern_id for match in first.matches] == [match.pattern_id for match in second.matches]
    assert first.matches[0].concept.canonical_intent == "repository_analysis"


def test_semantic_similarity_prefers_matching_intent_and_scope():
    request = SemanticPatternRecognitionRequest(isr=_isr("write_patch", "workspace"))
    result = SemanticPatternEngine().recognize(request)

    assert result.matches[0].concept.canonical_intent == "write_patch"
    assert result.matches[0].confidence >= 0.6


def test_semantic_confidence_scoring_uses_isr_structure():
    repository = SemanticKnowledgeRepository()
    entry = next(item for item in repository.list_entries() if item.canonical_intent == "repository_analysis")
    pattern = entry.patterns[0]
    normalized = SemanticPatternNormalizer().normalize(SemanticPatternRecognitionRequest(isr=_isr()))

    score = SemanticPatternScorer().score(entry, pattern, normalized)

    assert score > 0.8


def test_semantic_pattern_normalization_extracts_canonical_structure():
    normalized = SemanticPatternNormalizer().normalize(SemanticPatternRecognitionRequest(isr=_isr()))

    assert normalized["intent"] == "repository_analysis"
    assert normalized["scope"] == "repository"
    assert normalized["entities"] == ["repository"]
    assert normalized["constraints"]["read_only"] is True


def test_semantic_pattern_router_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    status = client.get("/api/v1/runtime/semantic-learning/patterns")
    assert status.status_code == 200
    assert status.json()["prompt_used"] is False

    response = client.post("/api/v1/runtime/semantic-learning/patterns", json={"isr": _isr().model_dump(mode="json")})
    assert response.status_code == 200
    assert response.json()["matches"][0]["concept"]["canonical_intent"] == "repository_analysis"
