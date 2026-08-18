from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from aipinho.services.rag.workspace_index_service import WorkspaceIndexService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspace-index"])


class IndexRequestBody(BaseModel):
    source_channel: str = "api"
    session_id: str | None = None


class WorkspaceSearchBody(BaseModel):
    query: str
    limit: int = 10


@router.post("/{workspace_id}/index/preview")
def preview_workspace_index(workspace_id: str, request: IndexRequestBody | None = None) -> dict[str, Any]:
    body = request or IndexRequestBody()
    return WorkspaceIndexService().preview(workspace_id=workspace_id, source_channel=body.source_channel, session_id=body.session_id)


@router.post("/{workspace_id}/index/start")
def start_workspace_index(workspace_id: str, request: IndexRequestBody | None = None) -> dict[str, Any]:
    body = request or IndexRequestBody()
    return WorkspaceIndexService().start(workspace_id=workspace_id, source_channel=body.source_channel, session_id=body.session_id)


@router.get("/{workspace_id}/index/status")
def workspace_index_status(workspace_id: str) -> dict[str, Any]:
    return WorkspaceIndexService().status(workspace_id)


@router.post("/{workspace_id}/search")
def search_workspace(workspace_id: str, request: WorkspaceSearchBody) -> dict[str, Any]:
    return WorkspaceIndexService().search(workspace_id=workspace_id, query=request.query, limit=request.limit)


@router.get("/{workspace_id}/search/health")
def workspace_search_health(workspace_id: str) -> dict[str, Any]:
    return WorkspaceIndexService().health(workspace_id)
