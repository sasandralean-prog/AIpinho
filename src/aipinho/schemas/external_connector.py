from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.external_gateway import GatewayClientType, GatewayRequest, GatewayResponse


ConnectorStatus = Literal["registered", "active", "disabled", "blocked"]
ConnectorAuthMode = Literal["none", "local_token", "bearer", "mcp_session"]


class ConnectorCapabilities(AIpinhoModel):
    can_create_session: bool = True
    can_send_request: bool = True
    can_receive_response: bool = True
    can_stream: bool = False
    can_upload_artifacts: bool = False
    can_modify_contracts: bool = False
    can_execute_runtime: bool = False
    capabilities: list[str] = Field(default_factory=list)


class ConnectorContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"connector_contract_{uuid4().hex}")
    connector_id: str
    version: str = "1.0"
    client_type: GatewayClientType
    auth_mode: ConnectorAuthMode = "local_token"
    supported_contracts: list[str] = Field(default_factory=lambda: ["conversation", "execution_plan"])
    input_format: str = "gateway_request.v1"
    output_format: str = "gateway_response.v1"
    compatibility: list[str] = Field(default_factory=lambda: ["external_gateway.v1"])


class ConnectorContext(AIpinhoModel):
    context_id: str = Field(default_factory=lambda: f"connector_context_{uuid4().hex}")
    connector_id: str
    client_type: GatewayClientType
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorLifecycle(AIpinhoModel):
    initialized: bool = False
    validated: bool = False
    active: bool = False
    shutdown: bool = False
    health: str = "unknown"


class ConnectorDefinition(AIpinhoModel):
    connector_id: str
    name: str
    version: str = "1.0"
    client_type: GatewayClientType
    capabilities: ConnectorCapabilities = Field(default_factory=ConnectorCapabilities)
    contract: ConnectorContract
    lifecycle: ConnectorLifecycle = Field(default_factory=ConnectorLifecycle)
    status: ConnectorStatus = "registered"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorRegisterRequest(AIpinhoModel):
    connector_id: str
    name: str
    version: str = "1.0"
    client_type: GatewayClientType
    auth_mode: ConnectorAuthMode = "local_token"
    supported_contracts: list[str] = Field(default_factory=lambda: ["conversation"])
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorRegistryView(AIpinhoModel):
    count: int
    connectors: list[ConnectorDefinition] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False


class ConnectorGatewayExchange(AIpinhoModel):
    exchange_id: str = Field(default_factory=lambda: f"connector_exchange_{uuid4().hex}")
    connector_id: str
    context: ConnectorContext
    gateway_request: GatewayRequest
    gateway_response: GatewayResponse | None = None
    status: str = "prepared"
    deterministic: bool = True
    mutates_runtime: bool = False
