from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.semantic_learning_router import router
from aipinho.schemas.semantic_learning import SemanticPatternRecognitionRequest, SemanticRecommendation, SemanticRecommendationRequest
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation
from aipinho.services.semantic_learning_service import RecommendationScorer, RecommendationValidator, SemanticPatternEngine, SemanticRecommendationEngine


def _pattern_matches():
    isr = IntermediateSemanticRepresentation(
        intent="repository_analysis",
        scope="repository",
        constraints={"read_only": True, "workspace_mutation": False},
        expected_outputs=["analysis_report"],
        ambiguity={"score": 0.2, "reasons": ["workspace resolution may be needed"]},
        confidence=0.9,
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )
    return SemanticPatternEngine().recognize(SemanticPatternRecognitionRequest(isr=isr)).matches


def _doctor_report():
    return {"findings": [{"category": "Intent", "reason_code": "intent_regression"}]}


def _matrix():
    return {"rows": [{"category": "Intent", "status": "FAIL", "reason_code": "intent_regression"}]}


def _patch_kb():
    return {"entries": [{"category": "intent_regression"}]}


def test_semantic_recommendations_are_traceable_and_pending():
    result = SemanticRecommendationEngine().recommend(
        SemanticRecommendationRequest(
            semantic_patterns=_pattern_matches(),
            doctor_report=_doctor_report(),
            regression_matrix=_matrix(),
            patch_knowledge_base=_patch_kb(),
        )
    )

    assert result.count >= 1
    recommendation = result.recommendations[0]
    assert recommendation.status == "pending_human_validation"
    assert recommendation.evidence
    assert recommendation.related_concept.canonical_intent == "repository_analysis"
    assert recommendation.modifies_semantic_interpreter is False
    assert recommendation.modifies_contract_compiler is False
    assert recommendation.modifies_governed_runtime is False
    assert recommendation.modifies_runtime_contracts is False
    assert recommendation.modifies_models is False


def test_recommendation_validator_rejects_automatic_mutation_flags():
    pattern = _pattern_matches()[0]
    recommendation = SemanticRecommendation(
        related_concept=pattern.concept,
        justification="bad",
        expected_benefit="bad",
        evidence=[],
        modifies_semantic_interpreter=True,
        modifies_contract_compiler=True,
        modifies_governed_runtime=True,
        modifies_runtime_contracts=True,
        modifies_models=True,
        status="accepted",
    )

    errors = RecommendationValidator().validate(recommendation)

    assert "semantic_recommendation_must_remain_pending_human_validation" in errors
    assert "semantic_recommendation_must_not_modify_semantic_interpreter" in errors
    assert "semantic_recommendation_requires_evidence" in errors


def test_recommendation_confidence_uses_pattern_and_evidence_context():
    pattern = _pattern_matches()[0]

    score_without_context = RecommendationScorer().score(pattern, [])
    score_with_context = RecommendationScorer().score(pattern, ["Intent"])

    assert score_with_context > score_without_context
    assert 0.0 <= score_with_context <= 1.0


def test_recommendation_router_create_list_and_get():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    created = client.post(
        "/api/v1/runtime/semantic-learning/recommendations",
        json={
            "semantic_patterns": [match.model_dump(mode="json") for match in _pattern_matches()],
            "doctor_report": _doctor_report(),
            "regression_matrix": _matrix(),
            "patch_knowledge_base": _patch_kb(),
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["pending_human_validation"] is True
    recommendation_id = payload["recommendations"][0]["recommendation_id"]

    listing = client.get("/api/v1/runtime/semantic-learning/recommendations")
    assert listing.status_code == 200
    assert any(item["recommendation_id"] == recommendation_id for item in listing.json()["recommendations"])

    fetched = client.get(f"/api/v1/runtime/semantic-learning/recommendations/{recommendation_id}")
    assert fetched.status_code == 200
    assert fetched.json()["recommendation_id"] == recommendation_id
