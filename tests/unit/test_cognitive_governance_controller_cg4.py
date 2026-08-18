from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.cognitive_governance_router import router
from aipinho.schemas.cognitive_governance import CognitiveGovernanceRequest
from aipinho.services.cognitive_policy_engine_service import CognitiveGovernanceController


def test_governance_controller_allows_safe_language_without_inference():
    decision = CognitiveGovernanceController().evaluate(
        CognitiveGovernanceRequest(
            role="semantic_interpreter",
            capability="language",
            risk="low",
            confidence=0.95,
            isr={"intent": "conversation", "confidence": 0.95},
            contracts={"operation_type": "conversation"},
        )
    )

    assert decision.status == "allowed"
    assert decision.allowed is True
    assert decision.model == "local-small"
    assert decision.inference_executed is False
    assert decision.audit.inference_executed is False
    assert len(decision.evidence) == 4


def test_governance_controller_requires_gates_from_policy_and_escalation():
    decision = CognitiveGovernanceController().evaluate(
        CognitiveGovernanceRequest(
            role="planner",
            capability="planning",
            risk="medium",
            confidence=0.5,
            isr={"intent": "project_plan"},
            contracts={"operation_type": "project_plan", "validation_required": True},
        )
    )

    assert decision.status == "requires_approval"
    assert decision.requires_approval is True
    assert decision.requires_supervisor is True
    assert decision.requires_runtime_doctor is True
    assert decision.requires_human_validation is True
    assert "approval_required" in decision.reason_codes


def test_governance_controller_blocks_role_permission_mismatch():
    decision = CognitiveGovernanceController().evaluate(
        CognitiveGovernanceRequest(
            role="ocr",
            capability="vision",
            risk="low",
            confidence=0.9,
            operator_approved=True,
            runtime_doctor_available=True,
        )
    )

    assert decision.status == "blocked"
    assert decision.allowed is False
    assert "role_not_bound_to_capability" in decision.reason_codes
    assert decision.route.status == "blocked"


def test_governance_controller_requests_human_validation_when_escalation_is_not_available():
    decision = CognitiveGovernanceController().evaluate(
        CognitiveGovernanceRequest(
            role="planner",
            capability="planning",
            risk="medium",
            confidence=0.3,
            operator_approved=True,
            supervisor_available=True,
            runtime_doctor_available=True,
            isr={"entities": ["workspace", "policy", "artifact"], "constraints": ["safe"], "expected_outputs": ["plan", "report"]},
            contracts={"requested_actions": ["plan", "review"], "validation_required": True, "approval_required": True},
        )
    )

    assert decision.status == "requires_approval"
    assert decision.escalation.action == "request_human_validation"
    assert decision.requires_human_validation is True
    assert decision.model == "local-reasoner"
    assert decision.audit.status == "requires_approval"
    assert decision.audit.evidence_ids == [item.evidence_id for item in decision.evidence]


def test_governance_controller_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    status = client.get("/api/v1/runtime/cognitive/governance")
    assert status.status_code == 200
    assert status.json()["inference_executed"] is False

    response = client.post(
        "/api/v1/runtime/cognitive/governance/evaluate",
        json={
            "role": "semantic_interpreter",
            "capability": "language",
            "risk": "low",
            "confidence": 0.9,
            "isr": {"intent": "conversation"},
            "contracts": {"operation_type": "conversation"},
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "allowed"
    assert response.json()["inference_executed"] is False
    assert response.json()["audit"]["route_id"] == response.json()["route"]["route_id"]

    history = client.get("/api/v1/runtime/cognitive/governance/history")
    assert history.status_code == 200
    assert history.json()["count"] >= 1
