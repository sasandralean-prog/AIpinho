from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.external_connector import ConnectorRegisterRequest
from aipinho.schemas.external_gateway import GatewayRequest, GatewaySessionRequest
from aipinho.services.external_connector_service import ConnectorRegistry
from aipinho.services.external_gateway_service import ExternalGateway


router = APIRouter(prefix="/api/v1/external", tags=["external-gateway"])


def _gateway() -> ExternalGateway:
    return ExternalGateway()


def _connectors() -> ConnectorRegistry:
    return ConnectorRegistry()


@router.post("/gateway")
def external_gateway(request: GatewayRequest) -> dict[str, object]:
    return _gateway().handle(request).model_dump(mode="json")


@router.post("/session")
def external_session(request: GatewaySessionRequest) -> dict[str, object]:
    return _gateway().create_session(request).model_dump(mode="json")


@router.get("/health")
def external_health() -> dict[str, object]:
    return _gateway().health()


@router.get("/version")
def external_version() -> dict[str, object]:
    return _gateway().version()


@router.get("/connectors")
def external_connectors() -> dict[str, object]:
    return _connectors().list().model_dump(mode="json")


@router.post("/connectors/register")
def external_connector_register(request: ConnectorRegisterRequest) -> dict[str, object]:
    return _connectors().register(request).model_dump(mode="json")


@router.get("/connectors/{connector_id}")
def external_connector_get(connector_id: str) -> dict[str, object]:
    connector = _connectors().get(connector_id)
    if connector is None:
        return {"status": "not_found", "connector_id": connector_id}
    return connector.model_dump(mode="json")
