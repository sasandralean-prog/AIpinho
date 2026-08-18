from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.cognitive_governance_router import router
from aipinho.schemas.cognitive_governance import CognitiveRoutingRequest
from aipinho.services.cognitive_policy_engine_service import CapabilityResolver, CognitiveRouter


def test_cognitive_router_routes_role_to_allowed_model_without_inference():
    decision = CognitiveRouter().route(
        CognitiveRoutingRequest(
            role="semantic_interpreter",
            capability="language",
            risk="low",
        )
    )

    assert decision.status == "allowed"
    assert decision.role == "semantic_interpreter"
    assert decision.model == "local-small"
    assert decision.inference_executed is False
    assert decision.prompt_interpreted is False


def test_cognitive_router_requires_gates_for_planning_escalation():
    decision = CognitiveRouter().route(
        CognitiveRoutingRequest(
            role="planner",
            capability="planning",
            risk="medium",
        )
    )

    assert decision.status == "requires_approval"
    assert decision.requires_approval is True
    assert decision.requires_supervisor is True
    assert decision.can_escalate is True
    assert "governed-reasoner" in decision.escalation_models


def test_cognitive_capability_resolver_uses_isr_and_contracts_not_prompt():
    resolver = CapabilityResolver()

    assert resolver.resolve(CognitiveRoutingRequest(role="planner", isr={"intent": "project_plan"})) == "planning"
    assert resolver.resolve(CognitiveRoutingRequest(role="patch_planner", contracts={"operation_type": "write_patch"})) == "code_generation"
    assert resolver.resolve(CognitiveRoutingRequest(role="vision", isr={"intent": "image_analysis"})) == "vision"


def test_cognitive_router_blocks_role_binding_mismatch():
    decision = CognitiveRouter().route(
        CognitiveRoutingRequest(
            role="ocr",
            capability="vision",
            risk="low",
            operator_approved=True,
            runtime_doctor_available=True,
        )
    )

    assert decision.status == "blocked"
    assert "role_not_bound_to_capability" in decision.reason_codes


def test_cognitive_router_allows_when_required_gates_satisfied():
    decision = CognitiveRouter().route(
        CognitiveRoutingRequest(
            role="patch_planner",
            capability="code_generation",
            risk="medium",
            operator_approved=True,
            supervisor_available=True,
            runtime_doctor_available=True,
        )
    )

    assert decision.status == "allowed"
    assert decision.requires_approval is False
    assert decision.requires_supervisor is False
    assert decision.inference_executed is False


def test_cognitive_router_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    routed = client.post(
        "/api/v1/runtime/cognitive/router",
        json={"role": "semantic_interpreter", "capability": "language", "risk": "low"},
    )
    assert routed.status_code == 200
    assert routed.json()["inference_executed"] is False

    routes = client.get("/api/v1/runtime/cognitive/routes")
    assert routes.status_code == 200
    assert routes.json()["count"] >= 1
