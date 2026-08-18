from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.pinhoforge_bridge import PinhoForgeBridgeRequest
from aipinho.services.pinhoforge_bridge import PinhoForgeBridgeClient

router = APIRouter(prefix="/api/v1/pinhoforge-bridge", tags=["pinhoforge-bridge"])


@router.get("/status")
def status() -> dict[str, object]:
    return {"status": "ok", "provider": PinhoForgeBridgeClient().status().model_dump()}


@router.post("/handshake")
def handshake(request: PinhoForgeBridgeRequest | None = None) -> dict[str, object]:
    bridge_request = request or PinhoForgeBridgeRequest(operation="handshake")
    response = PinhoForgeBridgeClient().request(bridge_request.model_copy(update={"operation": "handshake"}))
    return {"status": response.status, "response": response.model_dump()}


@router.get("/health")
def health() -> dict[str, object]:
    response = PinhoForgeBridgeClient().request(PinhoForgeBridgeRequest(operation="health"))
    return {"status": response.status, "response": response.model_dump()}


@router.get("/manifest")
def manifest() -> dict[str, object]:
    response = PinhoForgeBridgeClient().request(PinhoForgeBridgeRequest(operation="manifest"))
    return {"status": response.status, "response": response.model_dump()}


@router.get("/readiness")
def readiness() -> dict[str, object]:
    response = PinhoForgeBridgeClient().request(PinhoForgeBridgeRequest(operation="readiness"))
    return {"status": response.status, "response": response.model_dump()}


@router.post("/execute")
def execute(request: PinhoForgeBridgeRequest | None = None) -> dict[str, object]:
    bridge_request = request or PinhoForgeBridgeRequest(operation="execute")
    response = PinhoForgeBridgeClient().request(bridge_request.model_copy(update={"operation": "execute"}))
    return {"status": response.status, "response": response.model_dump()}
