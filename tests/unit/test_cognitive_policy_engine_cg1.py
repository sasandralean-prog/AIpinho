from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.cognitive_governance_router import router
from aipinho.schemas.cognitive_governance import CognitiveEvaluationRequest
from aipinho.services.cognitive_policy_engine_service import CognitivePolicyEngine


def test_policy_evaluation_allows_safe_language_without_inference():
    decision = CognitivePolicyEngine().evaluate(
        CognitiveEvaluationRequest(
            capability="language",
            model="local-small",
            risk="low",
            estimated_cost=0.05,
            estimated_latency_ms=1000,
        )
    )

    assert decision.status == "allowed"
    assert decision.allowed is True
    assert decision.inference_executed is False
    assert decision.deterministic is True


def test_risk_policy_blocks_high_risk_language_request():
    decision = CognitivePolicyEngine().evaluate(
        CognitiveEvaluationRequest(capability="language", model="local-small", risk="critical")
    )

    assert decision.status == "blocked"
    assert "risk_exceeds_policy" in decision.reason_codes
    assert decision.inference_executed is False


def test_capability_policy_blocks_forbidden_model():
    decision = CognitivePolicyEngine().evaluate(
        CognitiveEvaluationRequest(capability="vision", model="external-unsafe", risk="low")
    )

    assert decision.status == "blocked"
    assert "model_forbidden_by_policy" in decision.reason_codes


def test_approval_policy_requires_approval_supervisor_and_doctor_for_reasoning():
    decision = CognitivePolicyEngine().evaluate(
        CognitiveEvaluationRequest(capability="reasoning", model="local-reasoner", risk="medium")
    )

    assert decision.status == "requires_approval"
    assert decision.requires_approval is True
    assert decision.requires_supervisor is True
    assert decision.requires_runtime_doctor is True
    assert set(decision.reason_codes) == {"approval_required", "supervisor_required", "runtime_doctor_required"}


def test_approval_policy_allows_when_all_gates_are_satisfied():
    decision = CognitivePolicyEngine().evaluate(
        CognitiveEvaluationRequest(
            capability="reasoning",
            model="local-reasoner",
            risk="medium",
            operator_approved=True,
            supervisor_available=True,
            runtime_doctor_available=True,
        )
    )

    assert decision.status == "allowed"
    assert decision.allowed is True
    assert decision.reason_codes == []


def test_cognitive_policy_router_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    policies = client.get("/api/v1/runtime/cognitive/policies")
    assert policies.status_code == 200
    assert policies.json()["inference_executed"] is False
    policy_id = policies.json()["policies"][0]["policy_id"]

    policy = client.get(f"/api/v1/runtime/cognitive/policies/{policy_id}")
    assert policy.status_code == 200
    assert policy.json()["policy_id"] == policy_id

    evaluation = client.post(
        "/api/v1/runtime/cognitive/evaluate",
        json={"capability": "language", "model": "local-small", "risk": "low"},
    )
    assert evaluation.status_code == 200
    assert evaluation.json()["inference_executed"] is False
