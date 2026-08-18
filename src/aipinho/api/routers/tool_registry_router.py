from typing import Any

from fastapi import APIRouter, Body, HTTPException

from aipinho.services.tools.tool_contract_core import (
    GovernedToolRegistryService,
    ToolInvocationPreviewService,
    ToolPermissionService,
)
from aipinho.services.tools.tool_registry_service import ToolRegistryService

router = APIRouter(prefix="/api/v1/tool-registry", tags=["governed-tool-registry"])


@router.get("/status")
def governed_tool_status():
    governed = GovernedToolRegistryService().status()
    legacy = ToolRegistryService().load().status()
    return {
        "status": "ok" if governed["status"] == "ok" and legacy["status"] in {"ok", "degraded"} else "degraded",
        "registry": legacy,
        "governed_registry": governed,
        "real_execution_enabled": bool(legacy.get("real_execution_enabled")),
        "governed_real_execution_enabled": False,
        "write_execution_enabled": False,
        "shell_execution_enabled": False,
        "patch_apply_enabled": False,
    }


@router.get("/catalog")
def tool_catalog():
    tools = GovernedToolRegistryService().list_tools()
    return {"status": "ok", "count": len(tools), "tools": [tool.model_dump() for tool in tools], "real_execution_enabled": False}


@router.post("/permission/preview")
def tool_permission_preview(payload: dict[str, Any] = Body(...)):
    envelope = ToolPermissionService().preview(
        skill_id=str(payload.get("skill_id", "")),
        requested_tools=[str(item) for item in payload.get("requested_tools", [])],
        contract_allowed_tools=[str(item) for item in payload.get("allowed_tools", [])],
        contract_forbidden_tools=[str(item) for item in payload.get("forbidden_tools", [])],
        granted_capabilities=[str(item) for item in payload.get("granted_capabilities", [])],
        approval_id=str(payload["approval_id"]) if payload.get("approval_id") else None,
    )
    return {"status": "allowed" if not envelope.denied_tools else "blocked", "envelope": envelope.model_dump()}


@router.post("/invocation/preview")
def tool_invocation_preview(payload: dict[str, Any] = Body(...)):
    preview = ToolInvocationPreviewService().preview(
        tool_id=str(payload.get("tool_id", "")),
        input_data=dict(payload.get("input", {})),
        skill_id=str(payload["skill_id"]) if payload.get("skill_id") else None,
        call_mode=str(payload.get("call_mode", "preview_only")),
    )
    return preview.model_dump()


@router.get("/{tool_id}")
def governed_tool_detail(tool_id: str):
    governed = GovernedToolRegistryService().get(tool_id)
    if governed is not None:
        return {"status": "ok", "tool": governed.model_dump(), "registry": "governed"}
    legacy = ToolRegistryService().load().get_tool(tool_id)
    if legacy is not None:
        return {"status": "ok", "tool": legacy.model_dump(), "registry": "legacy_readonly"}
    raise HTTPException(status_code=404, detail="unknown_tool")
