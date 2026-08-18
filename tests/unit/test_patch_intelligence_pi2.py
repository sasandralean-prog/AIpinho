from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.patch_intelligence_router import router
from aipinho.schemas.patch_intelligence import PatchPatternRecognitionRequest
from aipinho.services.patch_intelligence_service import PatternConfidenceCalculator, PatternNormalizer, PatternScorer, PatchKnowledgeRepository, PatchPatternEngine


def _doctor_payload():
    return {
        "matrix": {
            "rows": [
                {"category": "Intent", "status": "FAIL", "severity": "high", "reason_code": "intent_regression"},
                {"category": "Validation", "status": "PASS", "severity": "info"},
            ]
        },
        "findings": [
            {
                "category": "Intent",
                "reason_code": "intent_regression",
                "suspected_modules": ["semantic_runtime", "runtime_dispatcher"],
            }
        ],
    }


def test_pattern_recognition_matches_canonical_category_without_prompt():
    result = PatchPatternEngine().recognize(PatchPatternRecognitionRequest(doctor_report=_doctor_payload(), regression_matrix=_doctor_payload()["matrix"]))

    assert result.count == 1
    assert result.prompt_used is False
    assert result.text_full_match_used is False
    assert result.matches[0].category == "intent_regression"
    assert result.matches[0].confidence > 0.8
    assert "semantic_runtime" in result.matches[0].suspected_modules


def test_pattern_confidence_calculation_is_bounded_and_deterministic():
    calculator = PatternConfidenceCalculator()

    assert calculator.confidence(1.7) == 1.0
    assert calculator.confidence(-1.0) == 0.0
    assert calculator.confidence(0.876) == 0.88


def test_pattern_false_positive_ignores_pass_and_unknown_categories():
    payload = {
        "matrix": {"rows": [{"category": "Unknown", "status": "FAIL"}, {"category": "Workspace", "status": "PASS"}]},
        "findings": [],
    }

    result = PatchPatternEngine().recognize(PatchPatternRecognitionRequest(doctor_report=payload, regression_matrix=payload["matrix"]))

    assert result.count == 0


def test_pattern_normalization_uses_structured_matrix_and_findings():
    normalized = PatternNormalizer().normalize(PatchPatternRecognitionRequest(doctor_report=_doctor_payload(), regression_matrix=_doctor_payload()["matrix"]))

    assert "intent_regression" in normalized
    assert normalized["intent_regression"]["statuses"] == ["FAIL"]
    assert normalized["intent_regression"]["reason_codes"] == ["intent_regression"]


def test_pattern_scorer_uses_category_metadata_not_full_text_prompt():
    repository = PatchKnowledgeRepository()
    entry = repository.get("patch_knowledge_intent_regression")
    assert entry is not None

    score = PatternScorer().score(entry, {"statuses": ["FAIL"], "reason_codes": ["intent_regression"], "suspected_modules": ["semantic_runtime"], "regressions": []})

    assert score > 0.8


def test_patch_intelligence_pattern_router_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    status = client.get("/api/v1/runtime/patch-intelligence/patterns")
    assert status.status_code == 200
    assert status.json()["prompt_used"] is False

    response = client.post(
        "/api/v1/runtime/patch-intelligence/patterns",
        json={"doctor_report": _doctor_payload(), "regression_matrix": _doctor_payload()["matrix"]},
    )
    assert response.status_code == 200
    assert response.json()["matches"][0]["category"] == "intent_regression"
