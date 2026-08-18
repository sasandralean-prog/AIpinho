from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from aipinho.services.security.local_token_service import LocalTokenService
from aipinho.services.supervisor.bootstrap_control_service import BootstrapControlService

router = APIRouter(prefix="/api/v1/bootstrap-control", tags=["bootstrap-control"])


def _require_token(authorization: str | None) -> None:
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="missing_or_invalid_bearer_token")


@router.get("/status")
def get_bootstrap_control_status() -> dict[str, object]:
    status = BootstrapControlService().status()
    return {"status": status.status, "bootstrap": status.model_dump()}


@router.post("/monitor/restart")
def restart_monitor_supervisor(authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    result = BootstrapControlService().restart_monitor(requested_by="mobile_or_local_operator")
    return {"status": result.status, "restart": result.model_dump()}
