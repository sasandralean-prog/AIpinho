from __future__ import annotations
from fastapi import APIRouter
from aipinho.schemas.supervisor.contracts import MobilePairingRequest
from aipinho.services.supervisor.supervisor_core import ConnectionProfileService, MobilePairingService
router = APIRouter(prefix="/api/v1/mobile", tags=["mobile-pairing"])
@router.get("/pairing/status")
def pairing_status() -> dict[str, object]:
    return {"status": "ok", "pairing": MobilePairingService().status()}
@router.post("/pairing/create-token")
def create_token() -> dict[str, object]:
    result = MobilePairingService().create_token()
    return {"status": result.status, "pairing": result.model_dump()}
@router.post("/pairing/rotate-token")
def rotate_token() -> dict[str, object]:
    result = MobilePairingService().rotate_token()
    return {"status": result.status, "pairing": result.model_dump()}
@router.post("/pairing/verify")
def verify_token(request: MobilePairingRequest) -> dict[str, object]:
    return MobilePairingService().verify(request.token, request.device_id)
@router.get("/dev-config")
def dev_config() -> dict[str, object]:
    svc = ConnectionProfileService(); selected = svc.get(svc.selected()); token_status = MobilePairingService().status()
    return {"status": "ok", "selected_profile": svc.selected(), "profile": selected.model_dump() if selected else None, "token_configured": token_status.get("token_configured"), "token": None}
