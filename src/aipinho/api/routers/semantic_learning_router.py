from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.semantic_learning import SemanticKnowledgeQuery, SemanticPatternRecognitionRequest, SemanticRecommendationRequest
from aipinho.schemas.semantic_learning import SemanticCurriculumPromoteRequest, SemanticCurriculumReviewRequest
from aipinho.services.semantic_learning_service import SemanticCurriculumService, SemanticKnowledgeQueryService, SemanticPatternEngine, SemanticRecommendationEngine


router = APIRouter(prefix="/api/v1/runtime/semantic-learning", tags=["semantic-learning"])


@router.get("/status")
def status() -> dict[str, object]:
    return SemanticKnowledgeQueryService().status()


@router.get("/knowledge")
def list_knowledge() -> dict[str, object]:
    return SemanticKnowledgeQueryService().list_entries().model_dump(mode="json")


@router.post("/query")
def query_knowledge(request: SemanticKnowledgeQuery) -> dict[str, object]:
    return SemanticKnowledgeQueryService().query(request).model_dump(mode="json")


@router.get("/concepts")
def list_concepts() -> dict[str, object]:
    return SemanticKnowledgeQueryService().concepts().model_dump(mode="json")


@router.get("/patterns")
def patterns_status() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "semantic_pattern_engine",
        "deterministic": True,
        "prompt_used": False,
        "modifies_runtime": False,
    }


@router.post("/patterns")
def recognize_patterns(request: SemanticPatternRecognitionRequest) -> dict[str, object]:
    return SemanticPatternEngine().recognize(request).model_dump(mode="json")


@router.post("/recommendations")
def create_recommendations(request: SemanticRecommendationRequest) -> dict[str, object]:
    return SemanticRecommendationEngine().recommend(request).model_dump(mode="json")


@router.get("/recommendations")
def list_recommendations() -> dict[str, object]:
    return SemanticRecommendationEngine().list().model_dump(mode="json")


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: str) -> dict[str, object]:
    recommendation = SemanticRecommendationEngine().get(recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="semantic_recommendation_not_found")
    return recommendation.model_dump(mode="json")


@router.get("/curriculum")
def get_curriculum() -> dict[str, object]:
    return SemanticCurriculumService().get().model_dump(mode="json")


@router.get("/curriculum/{entry_id}")
def get_curriculum_entry(entry_id: str) -> dict[str, object]:
    entry = SemanticCurriculumService().get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="semantic_curriculum_entry_not_found")
    return entry.model_dump(mode="json")


@router.post("/curriculum/promote")
def promote_curriculum(request: SemanticCurriculumPromoteRequest) -> dict[str, object]:
    try:
        return SemanticCurriculumService().promote(request).model_dump(mode="json")
    except KeyError:
        raise HTTPException(status_code=404, detail="semantic_curriculum_entry_not_found")


@router.post("/curriculum/review")
def review_curriculum(request: SemanticCurriculumReviewRequest) -> dict[str, object]:
    return SemanticCurriculumService().review(request).model_dump(mode="json")
