from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.cognitive_governance_router import router
from aipinho.schemas.cognitive_governance import CognitiveEscalationRequest, RoutingDecision
from aipinho.services.cognitive_policy_engine_service import CognitiveEscalationEngine, ComplexityEstimator, ConfidenceEvaluator


def _route(**overrides):
    values = {
        "status": "allowed",
        "role": "planner",
        "capability": "planning",
        "model": "local-reasoner",
        "policy_id": "cognitive_policy_planning_runtime",
        "can_escalate": True,
        "escalation_models": ["governed-reasoner"],
    }
    values.update(overrides)
    return RoutingDecision(**values)


def test_escalation_remains_when_confidence_high_complexity_low():
    decision = CognitiveEscalationEngine().escalate(
        CognitiveEscalationRequest(routing_decision=_route(), confidence=0.92, risk="low")
    )

    assert decision.action == "remain"
    assert decision.target_model is None
    assert decision.inference_executed is False
    assert "current_route_sufficient" in decision.reason_codes


def test_escalation_to_larger_model_when_low_confidence_high_complexity():
    decision = CognitiveEscalationEngine().escalate(
        CognitiveEscalationRequest(
            routing_decision=_route(),
            confidence=0.3,
            risk="medium",
            isr={"entities": ["a", "b", "c"], "constraints": ["safe"], "expected_outputs": ["report", "matrix"]},
            contracts={"requested_actions": ["plan", "review"], "validation_required": True, "approval_required": True},
        )
    )

    assert decision.action == "escalate"
    assert decision.target_model == "governed-reasoner"
    assert {"low_confidence", "high_complexity", "escalation_model_available"}.issubset(set(decision.reason_codes))


def test_escalation_requests_human_validation_when_no_escalation_model():
    decision = CognitiveEscalationEngine().escalate(
        CognitiveEscalationRequest(
            routing_decision=_route(can_escalate=False, escalation_models=[]),
            confidence=0.5,
            risk="medium",
        )
    )

    assert decision.action == "request_human_validation"
    assert decision.requires_human_validation is True
    assert "confidence_below_human_validation_threshold" in decision.reason_codes


def test_escalation_blocks_when_route_blocked_or_risk_critical():
    route_blocked = CognitiveEscalationEngine().escalate(
        CognitiveEscalationRequest(routing_decision=_route(status="blocked"), confidence=0.9, risk="low")
    )
    risk_blocked = CognitiveEscalationEngine().escalate(
        CognitiveEscalationRequest(routing_decision=_route(), confidence=0.9, risk="critical")
    )

    assert route_blocked.action == "block"
    assert route_blocked.blocked is True
    assert "routing_decision_blocked" in route_blocked.reason_codes
    assert risk_blocked.action == "block"
    assert "risk_exceeds_escalation_policy" in risk_blocked.reason_codes


def test_confidence_evaluator_clamps_and_uses_isr():
    evaluator = ConfidenceEvaluator()

    assert evaluator.evaluate(CognitiveEscalationRequest(routing_decision=_route(), confidence=1.8)) == 1.0
    assert evaluator.evaluate(CognitiveEscalationRequest(routing_decision=_route(), isr={"confidence": 0.42})) == 0.42


def test_complexity_estimator_uses_structures_not_prompt():
    estimator = ComplexityEstimator()
    request = CognitiveEscalationRequest(
        routing_decision=_route(),
        isr={
            "intent": "planning",
            "entities": ["workspace", "artifact"],
            "constraints": ["readonly", "approval"],
            "expected_outputs": ["report"],
            "prompt": "texto livre nao deve comandar a decisao",
        },
        contracts={"requested_actions": ["plan"], "validation_required": True},
    )

    assert estimator.estimate(request) > 0.4


def test_cognitive_escalation_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        "/api/v1/runtime/cognitive/escalate",
        json={
            "routing_decision": _route().model_dump(mode="json"),
            "confidence": 0.3,
            "risk": "medium",
            "isr": {"entities": ["project", "policy", "artifact"], "constraints": ["safe"], "expected_outputs": ["report"]},
            "contracts": {"requested_actions": ["plan", "review"], "validation_required": True, "approval_required": True},
        },
    )
    assert response.status_code == 200
    assert response.json()["action"] == "escalate"
    assert response.json()["inference_executed"] is False

    history = client.get("/api/v1/runtime/cognitive/escalation-history")
    assert history.status_code == 200
    assert history.json()["count"] >= 1
