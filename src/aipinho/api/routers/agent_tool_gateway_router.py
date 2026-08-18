from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Response

from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest, ToolInvocationCreateRequest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService


router = APIRouter(tags=["multi-agent-tool-gateway"])


def _service() -> AgentToolGatewayService:
    return AgentToolGatewayService()


@router.get("/api/v1/agent-tool-gateway/tools")
def list_tools(enabled: bool | None = None) -> dict[str, object]:
    service = _service()
    return {"status": "ok", "registry": service.registry.status().model_dump(), "tools": [tool.model_dump() for tool in service.list_tools(enabled=enabled)]}


@router.get("/api/v1/agent-tool-gateway/tools/{tool_name}")
def get_tool(tool_name: str) -> dict[str, object]:
    tool = _service().get_tool(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail="tool_not_found")
    return {"status": "ok", "tool": tool.model_dump()}


@router.post("/api/v1/agents/{agent_id}/runs/{run_id}/tools/{tool_name}/invoke")
def invoke_tool(agent_id: str, run_id: str, tool_name: str, request: ToolInvocationCreateRequest) -> dict[str, object]:
    try:
        result = _service().invoke(agent_id, run_id, tool_name, request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="agent_run_or_tool_not_found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="tool_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.model_dump()


@router.get("/api/v1/agents/runs/{run_id}/tools")
def list_run_tools(run_id: str) -> dict[str, object]:
    invocations = _service().list_invocations(run_id=run_id)
    return {"status": "ok", "run_id": run_id, "invocations": [invocation.model_dump() for invocation in invocations]}


@router.get("/api/v1/tools/invocations/{tool_invocation_id}")
def get_invocation(tool_invocation_id: str) -> dict[str, object]:
    invocation = _service().get_invocation(tool_invocation_id)
    if invocation is None:
        raise HTTPException(status_code=404, detail="tool_invocation_not_found")
    return {"status": "ok", "tool_invocation": invocation.model_dump()}


@router.post("/api/v1/tools/invocations/{tool_invocation_id}/cancel")
def cancel_invocation(tool_invocation_id: str) -> dict[str, object]:
    invocation = _service().cancel_invocation(tool_invocation_id)
    if invocation is None:
        raise HTTPException(status_code=404, detail="tool_invocation_not_found")
    return {"status": "ok", "tool_invocation": invocation.model_dump()}


@router.post("/api/v1/agents/{agent_id}/sessions/{session_id}/artifacts/upload")
def upload_agent_artifact(agent_id: str, session_id: str, request: ArtifactUploadRequest) -> dict[str, object]:
    artifact = _service().upload_artifact(agent_id, session_id, request)
    return {"status": "ok", "artifact": artifact.model_dump()}


@router.get("/api/v1/agents/{agent_id}/sessions/{session_id}/artifacts")
def list_agent_artifacts(agent_id: str, session_id: str) -> dict[str, object]:
    artifacts = _service().list_artifacts(agent_id, session_id)
    return {"status": "ok", "artifacts": [artifact.model_dump() for artifact in artifacts]}


@router.get("/api/v1/agents/artifacts/{artifact_id}/download")
def download_agent_artifact(artifact_id: str, authorization: str | None = Header(default=None)) -> Response:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authorization_bearer_required")
    try:
        artifact, content = _service().read_artifact_bytes(artifact_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc
    return Response(
        content=content,
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
