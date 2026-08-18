from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from aipinho.services.models.capability_router_service import CapabilityRouterService

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


class WorkspaceSearchRequest(BaseModel):
    query: str
    workspace_path: str
    limit: int = 10


@router.get("")
def list_capabilities() -> dict[str, Any]:
    service = CapabilityRouterService()
    return {"status": "ok", "capabilities": service.capabilities()}


@router.get("/health")
def capability_health() -> dict[str, Any]:
    return CapabilityRouterService().health()


@router.post("/workspace-search")
def workspace_search(request: WorkspaceSearchRequest) -> dict[str, Any]:
    return CapabilityRouterService().workspace_search(query=request.query, workspace_path=request.workspace_path, limit=request.limit)
