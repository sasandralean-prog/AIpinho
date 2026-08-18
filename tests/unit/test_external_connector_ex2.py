from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.external_gateway_router import router
from aipinho.schemas.external_connector import ConnectorCapabilities, ConnectorDefinition, ConnectorContract, ConnectorRegisterRequest
from aipinho.schemas.external_gateway import GatewayRequest
from aipinho.services.external_connector_service import ConnectorFramework, ConnectorRegistry


def test_connector_registry_registers_all_official_connectors():
    registry = ConnectorRegistry()
    view = registry.list()
    ids = {connector.connector_id for connector in view.connectors}

    assert {"launcher", "cli", "vscode", "continue", "rest", "web", "mobile", "mcp"}.issubset(ids)
    assert all(connector.status == "active" for connector in view.connectors)
    assert all(connector.capabilities.can_execute_runtime is False for connector in view.connectors)
    assert all(connector.capabilities.can_modify_contracts is False for connector in view.connectors)


def test_connector_contracts_are_common_and_gateway_compatible():
    connector = ConnectorRegistry().get("continue")

    assert connector is not None
    assert connector.contract.input_format == "gateway_request.v1"
    assert connector.contract.output_format == "gateway_response.v1"
    assert "external_gateway.v1" in connector.contract.compatibility
    assert connector.contract.client_type == "continue"


def test_connector_registration_lifecycle_blocks_runtime_execution_capability():
    registry = ConnectorRegistry()
    blocked = registry.register_definition(
        ConnectorDefinition(
            connector_id="unsafe",
            name="UnsafeConnector",
            client_type="future",
            capabilities=ConnectorCapabilities(can_execute_runtime=True),
            contract=ConnectorContract(connector_id="unsafe", client_type="future"),
        )
    )

    assert blocked.status == "blocked"
    assert blocked.lifecycle.validated is False
    assert blocked.lifecycle.health == "blocked"


def test_connector_framework_sends_through_gateway_not_runtime():
    exchange = ConnectorFramework().send(
        "vscode",
        GatewayRequest(
            client_id="vscode_2",
            client_type="vscode",
            version="1.0",
            target_module="planner",
            contract={"contract_type": "execution_plan"},
        ),
    )

    assert exchange.status == "accepted"
    assert exchange.gateway_response is not None
    assert exchange.gateway_response.kernel_status == "ready"
    assert exchange.mutates_runtime is False


def test_connector_framework_rejects_client_type_mismatch():
    try:
        ConnectorFramework().prepare_gateway_request(
            "mobile",
            GatewayRequest(client_id="web_1", client_type="web", target_module="planner", contract={"contract_type": "execution_plan"}),
        )
    except ValueError as exc:
        assert str(exc) == "connector_client_type_mismatch"
    else:
        raise AssertionError("connector mismatch should fail")


def test_external_connector_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    listed = client.get("/api/v1/external/connectors")
    assert listed.status_code == 200
    assert listed.json()["count"] >= 8

    created = client.post(
        "/api/v1/external/connectors/register",
        json={
            "connector_id": "custom_rest_test",
            "name": "Custom REST Test",
            "client_type": "rest",
            "version": "1.0",
            "supported_contracts": ["conversation"],
            "capabilities": ["gateway_request"],
        },
    )
    assert created.status_code == 200
    assert created.json()["status"] == "active"

    fetched = client.get("/api/v1/external/connectors/custom_rest_test")
    assert fetched.status_code == 200
    assert fetched.json()["connector_id"] == "custom_rest_test"
