from __future__ import annotations
from fastapi import APIRouter
from aipinho.services.supervisor.supervisor_core import MonitorStatusBuilder, ServiceManifestService
router = APIRouter(prefix="/api/v1/supervisor", tags=["supervisor"])
@router.get("/status")
def get_supervisor_status() -> dict[str, object]:
    return {"status": "ok", "manifest": ServiceManifestService().status(), "supervisor": MonitorStatusBuilder().status().model_dump()}
