from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from aipinho.services.security.local_token_service import LocalTokenService
from aipinho.services.supervisor.backend_control_service import BackendControlService

router = APIRouter(prefix="/api/v1/backend-control", tags=["backend-control"])


def _require_token(authorization: str | None) -> None:
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="missing_or_invalid_bearer_token")


def _served_port(request: Request) -> int | None:
    header = request.headers.get("x-aipinho-served-port")
    if header and header.isdigit():
        return int(header)
    return request.url.port


@router.get("/status")
def get_backend_control_status() -> dict[str, object]:
    status = BackendControlService().status()
    return {"status": status.status, "backend": status.model_dump()}


@router.post("/restart")
def restart_backend(request: Request, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    result = BackendControlService().restart(served_port=_served_port(request), requested_by="mobile_or_local_operator")
    return {"status": result.status, "restart": result.model_dump()}
