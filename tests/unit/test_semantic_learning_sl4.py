from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.semantic_learning_router import router
from aipinho.schemas.semantic_learning import SemanticCurriculumPromoteRequest, SemanticCurriculumReviewRequest
from aipinho.services.semantic_learning_service import SemanticCurriculumSerializer, SemanticCurriculumService


def test_semantic_curriculum_organizes_knowledge_into_competencies():
    result = SemanticCurriculumService().get()

    curriculum = result.curriculum
    assert curriculum.auto_changes_runtime is False
    assert curriculum.entries
    assert curriculum.capabilities
    assert result.report_markdown.startswith("# Semantic Curriculum Report")
    assert result.evolution_history["semantic_evolution_history"]
    first = curriculum.entries[0]
    assert first.competency.name
    assert first.competency.knowledge_used
    assert first.maturity in {"LEARNING", "STABLE"}


def test_semantic_curriculum_serializer_roundtrip_preserves_version():
    result = SemanticCurriculumService().get()
    serializer = SemanticCurriculumSerializer()

    restored = serializer.from_json(serializer.to_json(result.curriculum))

    assert restored.version.version == result.curriculum.version.version
    assert len(restored.entries) == len(result.curriculum.entries)


def test_semantic_promotion_candidate_requires_approval_and_does_not_modify_runtime():
    service = SemanticCurriculumService()
    entry_id = service.get().curriculum.entries[0].curriculum_entry_id

    candidate = service.promote(
        SemanticCurriculumPromoteRequest(
            curriculum_entry_id=entry_id,
            reason="Promote only as a future governed version candidate.",
            expected_impact="Improve interpretation consistency.",
        )
    )

    assert candidate.approval_required is True
    assert candidate.status == "candidate"
    assert candidate.auto_promoted is False
    assert candidate.modifies_runtime is False
    assert candidate.rollback


def test_semantic_curriculum_review_records_history_without_runtime_change():
    service = SemanticCurriculumService()
    before = len(service.get().curriculum.evolutions)

    result = service.review(
        SemanticCurriculumReviewRequest(
            recommendation_id="semantic_recommendation_test",
            decision="accepted",
            rationale="Accepted as curriculum evidence only.",
        )
    )

    assert result.curriculum.auto_changes_runtime is False
    assert len(result.curriculum.evolutions) == before + 1
    assert "review:accepted:semantic_recommendation_test" in result.curriculum.evolutions[-1].changes


def test_semantic_curriculum_router_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    curriculum = client.get("/api/v1/runtime/semantic-learning/curriculum")
    assert curriculum.status_code == 200
    payload = curriculum.json()
    assert payload["curriculum"]["auto_changes_runtime"] is False
    entry_id = payload["curriculum"]["entries"][0]["curriculum_entry_id"]

    entry = client.get(f"/api/v1/runtime/semantic-learning/curriculum/{entry_id}")
    assert entry.status_code == 200
    assert entry.json()["curriculum_entry_id"] == entry_id

    promote = client.post(
        "/api/v1/runtime/semantic-learning/curriculum/promote",
        json={
            "curriculum_entry_id": entry_id,
            "reason": "Create a candidate only.",
            "expected_impact": "Improve future semantic runtime consistency.",
        },
    )
    assert promote.status_code == 200
    assert promote.json()["approval_required"] is True
    assert promote.json()["auto_promoted"] is False

    review = client.post(
        "/api/v1/runtime/semantic-learning/curriculum/review",
        json={"recommendation_id": "semantic_recommendation_router", "decision": "rejected", "rationale": "Not mature enough."},
    )
    assert review.status_code == 200
    assert review.json()["curriculum"]["auto_changes_runtime"] is False
