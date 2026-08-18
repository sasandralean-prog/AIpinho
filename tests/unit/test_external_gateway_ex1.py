from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.external_gateway_router import router
from aipinho.schemas.external_gateway import GatewayRequest, GatewaySessionRequest
from aipinho.services.external_gateway_service import ExternalGateway


def test_external_gateway_creates_session_for_supported_client():
    session = ExternalGateway().create_session(GatewaySessionRequest(client_id="launcher_1", client_type="launcher", version="1.0"))

    assert session.status == "active"
    assert session.client_type == "launcher"
    assert session.gateway_session_id.startswith("gateway_session_")


def test_external_gateway_blocks_unsupported_version():
    session = ExternalGateway().create_session(GatewaySessionRequest(client_id="cli_1", client_type="cli", version="0.1"))

    assert session.status == "blocked"
    assert "gateway_version_not_supported" in session.metadata["reason_codes"]


def test_external_gateway_blocks_direct_internal_module_access():
    response = ExternalGateway().handle(
        GatewayRequest(
            client_id="rest_1",
            client_type="rest",
            version="1.0",
            target_module="semantic_runtime",
            contract={"contract_type": "conversation"},
        )
    )

    assert response.status == "blocked"
    assert "direct_internal_module_access_forbidden" in response.reason_codes
    assert response.internal_access_granted is False
    assert response.kernel_status == "not_dispatched"


def test_external_gateway_requires_contract_before_kernel_dispatch():
    response = ExternalGateway().handle(
        GatewayRequest(
            client_id="mobile_1",
            client_type="mobile",
            version="1.0",
            target_module="planner",
            contract={},
        )
    )

    assert response.status == "blocked"
    assert "contract_key_missing:contract_type" in response.reason_codes
    assert response.kernel_status == "not_dispatched"


def test_external_gateway_dispatches_supported_request_to_kernel():
    response = ExternalGateway().handle(
        GatewayRequest(
            client_id="vscode_1",
            client_type="vscode",
            version="1.0",
            target_module="planner",
            contract={"contract_type": "execution_plan"},
        )
    )

    assert response.status == "accepted"
    assert response.kernel_status == "ready"
    assert response.kernel_result["module_id"] == "planner"
    assert response.governed is True
    assert response.internal_access_granted is False
    assert response.mutates_runtime is False


def test_external_gateway_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    session = client.post("/api/v1/external/session", json={"client_id": "continue_1", "client_type": "continue", "version": "1.0"})
    assert session.status_code == 200
    assert session.json()["status"] == "active"

    gateway = client.post(
        "/api/v1/external/gateway",
        json={"client_id": "continue_1", "client_type": "continue", "version": "1.0", "target_module": "planner", "contract": {"contract_type": "execution_plan"}},
    )
    assert gateway.status_code == 200
    assert gateway.json()["status"] == "accepted"

    health = client.get("/api/v1/external/health")
    assert health.status_code == 200
    assert health.json()["mutates_runtime"] is False

    version = client.get("/api/v1/external/version")
    assert version.status_code == 200
    assert version.json()["contract"] == "external_gateway.v1"
