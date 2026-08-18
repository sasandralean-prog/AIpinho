from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.services.tools.tool_dry_run_executor import ToolDryRunExecutor
from aipinho.services.tools.tool_input_validator import ToolInputValidator
from aipinho.services.tools.tool_preview_service import ToolPreviewService
from aipinho.services.tools.tool_registry_service import ToolRegistryService
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService
from aipinho.services.tools.tool_contract_core import (
    GovernedToolRegistryService,
    ToolInvocationPreviewService,
    ToolPermissionService,
)
from aipinho.services.tools.tool_safety_service import ToolSafetyService

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


def _dump_model(value: Any):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _parse_calls(payload: Any) -> list[ToolCall]:
    try:
        if isinstance(payload, list):
            return [ToolCall.model_validate(item) for item in payload]
        if isinstance(payload, dict) and "tool_calls" in payload:
            calls = payload.get("tool_calls")
            if not isinstance(calls, list):
                raise ValueError("tool_calls_must_be_list")
            return [ToolCall.model_validate(item) for item in calls]
        if isinstance(payload, dict) and "tool_call" in payload:
            return [ToolCall.model_validate(payload["tool_call"])]
        if isinstance(payload, dict):
            return [ToolCall.model_validate(payload)]
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(status_code=422, detail="invalid_tool_call_payload")


@router.get("")
def list_tools() -> dict[str, object]:
    registry = ToolRegistryService().load()
    return {"status": "ok", "tools": [_dump_model(tool) for tool in registry.list_tools()]}


@router.get("/status")
def get_tools_status() -> dict[str, object]:
    registry = ToolRegistryService().load()
    executor = ToolDryRunExecutor()
    readonly = ReadOnlyExecutionService().status()
    registry_status = registry.status()
    governed = registry_status.get("governed_execution_enabled") is True
    return {
        "status": "ok" if registry_status.get("status") == "ok" and readonly.get("status") == "ok" else "degraded",
        "registry": registry_status,
        "executor": executor.status(),
        "read_only_execution": readonly,
        "real_execution_enabled": True,
        "write_execution_enabled": False,
        "shell_execution_enabled": governed,
        "governed_execution_enabled": governed,
        "patch_apply_enabled": False,
    }


@router.get("/catalog")
def tool_catalog() -> dict[str, object]:
    tools = GovernedToolRegistryService().list_tools()
    return {"status": "ok", "count": len(tools), "tools": [tool.model_dump() for tool in tools], "real_execution_enabled": False}


@router.post("/permission/preview")
def tool_permission_preview(payload: dict[str, Any] = Body(...)) -> dict[str, object]:
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
def tool_invocation_preview(payload: dict[str, Any] = Body(...)) -> dict[str, object]:
    preview = ToolInvocationPreviewService().preview(
        tool_id=str(payload.get("tool_id", "")),
        input_data=dict(payload.get("input", {})),
        skill_id=str(payload["skill_id"]) if payload.get("skill_id") else None,
        call_mode=str(payload.get("call_mode", "preview_only")),
    )
    return preview.model_dump()


@router.get("/{tool_id}")
def get_tool(tool_id: str) -> dict[str, object]:
    governed = GovernedToolRegistryService().get(tool_id)
    if governed is not None:
        return {"status": "ok", "tool": governed.model_dump(), "registry": "governed"}
    tool = ToolRegistryService().load().get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="unknown_tool")
    return {"status": "ok", "tool": tool, "registry": "legacy_readonly"}


@router.post("/validate")
def validate_tool(payload: Any = Body(...)) -> dict[str, object]:
    calls = _parse_calls(payload)
    registry = ToolRegistryService().load()
    validator = ToolInputValidator()
    safety_service = ToolSafetyService(registry=registry, validator=validator)
    results = []
    for call in calls:
        safety, tool, _ = safety_service.check(call)
        validation = validator.validate(tool, call) if tool else None
        results.append({"tool_call_id": call.tool_call_id, "tool_id": call.tool_id, "tool_known": tool is not None, "validation": validation, "safety": safety})
    overall = "valid" if all(item["tool_known"] and item["safety"].status in {"allowed", "needs_approval"} for item in results) else "blocked"
    return {"status": overall, "results": results, "real_execution_enabled": False}


@router.post("/preview")
def preview_tools(payload: Any = Body(...)) -> dict[str, object]:
    calls = _parse_calls(payload)
    plan = ToolPreviewService().plan_from_calls(calls, source="direct")
    return {"status": "ok", "plan": plan, "real_execution_enabled": False}


@router.post("/dry-run")
def dry_run_tools(payload: Any = Body(...)) -> dict[str, object]:
    calls = _parse_calls(payload)
    plan = ToolPreviewService().plan_from_calls(calls, source="direct")
    execute_mode_calls = [call for call in calls if call.mode == "execute"]
    if execute_mode_calls:
        result = {
            "dry_run_id": plan.dry_run_id,
            "status": "blocked",
            "tool_results": [
                {
                    "tool_id": call.tool_id,
                    "status": "blocked",
                    "would_do": "execute_mode_requested; /api/v1/tools/dry-run never executes tools. Use the governed execution pipeline with approval.",
                    "would_use_actions": [],
                    "would_require_capabilities": [],
                    "would_require_approval": [],
                    "potential_side_effects": [],
                    "input_valid": False,
                    "warnings": ["execute_mode_requested"],
                    "trace": [],
                }
                for call in execute_mode_calls
            ],
            "safe_to_execute": False,
            "summary": "Dry-run blocked because execute mode was requested on a dry-run endpoint.",
            "warnings": ["execute_mode_requested"],
            "trace": list(plan.trace),
        }
        return {"status": "blocked", "plan": plan, "result": result, "real_execution_enabled": False}
    result = ToolDryRunExecutor().dry_run(plan)
    return {"status": result.status, "plan": plan, "result": result, "real_execution_enabled": False}


@router.post("/dry-run/from-preview/{preview_id}")
def dry_run_from_preview(preview_id: str) -> dict[str, object]:
    plan = ToolPreviewService().plan_from_preview(preview_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="preview_not_found")
    result = ToolDryRunExecutor().dry_run(plan)
    return {"status": result.status, "plan": plan, "result": result, "real_execution_enabled": False}


@router.post("/dry-run/from-draft/{draft_id}")
def dry_run_from_draft(draft_id: str) -> dict[str, object]:
    plan = ToolPreviewService().plan_from_draft(draft_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="draft_not_found")
    result = ToolDryRunExecutor().dry_run(plan)
    return {"status": result.status, "plan": plan, "result": result, "real_execution_enabled": False}
