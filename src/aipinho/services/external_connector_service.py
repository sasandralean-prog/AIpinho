from __future__ import annotations

from aipinho.schemas.external_connector import (
    ConnectorCapabilities,
    ConnectorContract,
    ConnectorContext,
    ConnectorDefinition,
    ConnectorGatewayExchange,
    ConnectorRegisterRequest,
    ConnectorRegistryView,
)
from aipinho.schemas.external_gateway import GatewayRequest
from aipinho.services.external_gateway_service import ExternalGateway


class ConnectorLifecycleService:
    def initialize(self, connector: ConnectorDefinition) -> ConnectorDefinition:
        lifecycle = connector.lifecycle.model_copy(update={"initialized": True, "health": "initializing"})
        return connector.model_copy(update={"lifecycle": lifecycle})

    def validate(self, connector: ConnectorDefinition) -> ConnectorDefinition:
        blocked = connector.capabilities.can_modify_contracts or connector.capabilities.can_execute_runtime
        lifecycle = connector.lifecycle.model_copy(update={"validated": not blocked, "active": not blocked, "health": "blocked" if blocked else "ok"})
        return connector.model_copy(update={"lifecycle": lifecycle, "status": "blocked" if blocked else "active"})

    def shutdown(self, connector: ConnectorDefinition) -> ConnectorDefinition:
        lifecycle = connector.lifecycle.model_copy(update={"shutdown": True, "active": False, "health": "shutdown"})
        return connector.model_copy(update={"lifecycle": lifecycle, "status": "disabled"})


class ConnectorRegistry:
    _connectors: dict[str, ConnectorDefinition] = {}

    def __init__(self, lifecycle: ConnectorLifecycleService | None = None) -> None:
        self.lifecycle = lifecycle or ConnectorLifecycleService()
        if not self._connectors:
            for connector in self._official_connectors():
                self.register_definition(connector)

    def list(self) -> ConnectorRegistryView:
        return ConnectorRegistryView(count=len(self._connectors), connectors=sorted(self._connectors.values(), key=lambda item: item.connector_id))

    def get(self, connector_id: str) -> ConnectorDefinition | None:
        return self._connectors.get(connector_id)

    def register(self, request: ConnectorRegisterRequest) -> ConnectorDefinition:
        definition = ConnectorDefinition(
            connector_id=request.connector_id,
            name=request.name,
            version=request.version,
            client_type=request.client_type,
            capabilities=ConnectorCapabilities(capabilities=request.capabilities),
            contract=ConnectorContract(
                connector_id=request.connector_id,
                version=request.version,
                client_type=request.client_type,
                auth_mode=request.auth_mode,
                supported_contracts=request.supported_contracts,
            ),
            metadata=request.metadata,
        )
        return self.register_definition(definition)

    def register_definition(self, definition: ConnectorDefinition) -> ConnectorDefinition:
        initialized = self.lifecycle.initialize(definition)
        validated = self.lifecycle.validate(initialized)
        self._connectors[validated.connector_id] = validated
        return validated

    def _official_connectors(self) -> list[ConnectorDefinition]:
        specs = [
            ("launcher", "LauncherConnector", "launcher"),
            ("cli", "CLIConnector", "cli"),
            ("vscode", "VSCodeConnector", "vscode"),
            ("continue", "ContinueConnector", "continue"),
            ("rest", "RESTConnector", "rest"),
            ("web", "WebConnector", "web"),
            ("mobile", "MobileConnector", "mobile"),
            ("mcp", "MCPConnector", "mcp"),
        ]
        return [
            ConnectorDefinition(
                connector_id=connector_id,
                name=name,
                client_type=client_type,  # type: ignore[arg-type]
                capabilities=ConnectorCapabilities(can_stream=connector_id in {"continue", "web"}, capabilities=["gateway_request", "gateway_response"]),
                contract=ConnectorContract(connector_id=connector_id, client_type=client_type),  # type: ignore[arg-type]
            )
            for connector_id, name, client_type in specs
        ]


class ConnectorFramework:
    def __init__(self, registry: ConnectorRegistry | None = None, gateway: ExternalGateway | None = None) -> None:
        self.registry = registry or ConnectorRegistry()
        self.gateway = gateway or ExternalGateway()

    def prepare_gateway_request(self, connector_id: str, request: GatewayRequest) -> ConnectorGatewayExchange:
        connector = self.registry.get(connector_id)
        if connector is None:
            raise ValueError("connector_not_registered")
        if connector.status != "active":
            raise ValueError("connector_not_active")
        if connector.client_type != request.client_type:
            raise ValueError("connector_client_type_mismatch")
        context = ConnectorContext(connector_id=connector.connector_id, client_type=connector.client_type)
        return ConnectorGatewayExchange(connector_id=connector.connector_id, context=context, gateway_request=request)

    def send(self, connector_id: str, request: GatewayRequest) -> ConnectorGatewayExchange:
        exchange = self.prepare_gateway_request(connector_id, request)
        response = self.gateway.handle(request)
        return exchange.model_copy(update={"gateway_response": response, "status": response.status})
