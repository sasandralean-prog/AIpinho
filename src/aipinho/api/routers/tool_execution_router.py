from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService

router = APIRouter(prefix="/api/v1/tools", tags=["tool-execution"])


def _parse_tool_inputs(payload: Any) -> list[dict[str, Any]] | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        if "tool_inputs" in payload:
            value = payload.get("tool_inputs")
            if value is None:
                return None
            if not isinstance(value, list):
                raise HTTPException(status_code=422, detail="tool_inputs_must_be_list")
            return [item for item in value if isinstance(item, dict)]
        if "tool_id" in payload:
            return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return None


@router.get("/execution-status")
def get_execution_status() -> dict[str, object]:
    read_only_status = ReadOnlyExecutionService().status()
    governed_status = GovernedToolExecutionService().status()
    return {
        "status": "ok",
        **read_only_status,
        "read_only": read_only_status,
        "governed": governed_status,
    }


@router.post("/execute-readonly")
def execute_readonly(payload: Any = Body(...)) -> dict[str, object]:
    try:
        request = ToolExecutionRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = ReadOnlyExecutionService().execute(request)
    return {"status": result.status, "result": result, "real_execution_enabled": True, "write_execution_enabled": False}


@router.get("/governed/status")
def get_governed_execution_status() -> dict[str, object]:
    return GovernedToolExecutionService().status()


@router.post("/governed/request-approval")
def request_governed_tool_approval(payload: Any = Body(...)) -> dict[str, object]:
    try:
        request = ToolExecutionRequest.model_validate({**payload, "mode": "governed"} if isinstance(payload, dict) else payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return GovernedToolExecutionService().request_approval(request)


@router.post("/governed/execute")
def execute_governed_tool(payload: Any = Body(...)) -> dict[str, object]:
    try:
        request = ToolExecutionRequest.model_validate({**payload, "mode": "governed"} if isinstance(payload, dict) else payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = GovernedToolExecutionService().execute(request)
    return {"status": result.status, "result": result, "real_execution_enabled": True, "governed_execution_enabled": True}


@router.post("/execute-readonly/from-preview/{preview_id}")
def execute_readonly_from_preview(preview_id: str, payload: Any = Body(default=None)) -> dict[str, object]:
    bundle = ReadOnlyExecutionService().execute_from_preview(preview_id, tool_inputs=_parse_tool_inputs(payload))
    if bundle is None:
        raise HTTPException(status_code=404, detail="preview_not_found")
    return {"status": bundle.status, "bundle": bundle}


@router.post("/execute-readonly/from-draft/{draft_id}")
def execute_readonly_from_draft(draft_id: str, payload: Any = Body(default=None)) -> dict[str, object]:
    bundle = ReadOnlyExecutionService().execute_from_draft(draft_id, tool_inputs=_parse_tool_inputs(payload))
    if bundle is None:
        raise HTTPException(status_code=404, detail="draft_not_found")
    return {"status": bundle.status, "bundle": bundle}


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str) -> dict[str, object]:
    result = ReadOnlyExecutionService().get_execution(execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="execution_not_found")
    return {"status": "ok", "execution": result}


@router.get("/executions/{execution_id}/events")
def get_execution_events(execution_id: str) -> dict[str, object]:
    events = ReadOnlyExecutionService().get_events(execution_id)
    if not events:
        raise HTTPException(status_code=404, detail="execution_events_not_found")
    return {"status": "ok", "events": events}
