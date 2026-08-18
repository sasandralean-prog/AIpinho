from typing import Any

from fastapi import APIRouter, Body, HTTPException

from aipinho.schemas.skills.contracts import SkillDryRunRequest, SkillExecutionRequest, SkillPreviewRequest, SkillRouteRequest
from aipinho.services.skills.skill_execution_service import SkillExecutionService
from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService
from aipinho.services.skills.skill_runtime_core import (
    SkillComposerService,
    SkillContractValidator,
    SkillDryRunService,
    SkillOutputValidator,
    SkillPreviewService,
    SkillRouterService,
    SkillTraceService,
)

router = APIRouter(prefix="/api/v1/skills", tags=["skill-runtime"])


@router.get("")
def list_skill_manifests(
    category: str | None = None,
    agent_id: str | None = None,
    project_stack: str | None = None,
    include_archived: bool = False,
):
    registry = SkillManifestRegistryService()
    return {
        "status": "ok",
        "skills": [
            item.model_dump()
            for item in registry.list_manifests(
                category=category,
                agent_id=agent_id,
                project_stack=project_stack,
                include_archived=include_archived,
            )
        ],
    }


@router.get("/health")
def skill_health():
    return SkillManifestRegistryService().health()


@router.get("/categories")
def skill_categories():
    return SkillManifestRegistryService().categories()


@router.post("/registry/reload")
def reload_skill_registry():
    registry = SkillManifestRegistryService()
    return {"status": "ok", "registry": registry.status().model_dump()}


@router.post("/{skill_id}/enable")
def enable_skill(skill_id: str):
    try:
        return {"status": "ok", "skill": SkillManifestRegistryService().set_status(skill_id, "active").model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="skill_not_found") from exc


@router.post("/{skill_id}/disable")
def disable_skill(skill_id: str):
    try:
        return {"status": "ok", "skill": SkillManifestRegistryService().set_status(skill_id, "disabled").model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="skill_not_found") from exc


@router.post("/{skill_id}/execute")
def execute_skill(skill_id: str, request: SkillExecutionRequest):
    if request.skill_id != skill_id:
        raise HTTPException(status_code=400, detail="skill_id_mismatch")
    return SkillExecutionService().execute(request).model_dump()


@router.get("/executions/{skill_execution_id}")
def get_skill_execution(skill_execution_id: str):
    result = SkillExecutionService().get(skill_execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="skill_execution_not_found")
    return {"status": "ok", "skill_execution": result.model_dump()}


@router.get("/executions/{skill_execution_id}/trace")
def get_skill_execution_trace(skill_execution_id: str):
    trace = SkillExecutionService().trace(skill_execution_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="skill_execution_not_found")
    return trace


@router.post("/validate")
def validate_skill(payload: dict[str, Any] = Body(...)):
    return SkillContractValidator().validate(payload)


@router.post("/route")
def route_skill(request: SkillRouteRequest):
    return SkillRouterService().route(request).model_dump()


@router.post("/preview")
def preview_skill(request: SkillPreviewRequest):
    return SkillPreviewService().preview(request).model_dump()


@router.post("/dry-run")
def dry_run_skill(request: SkillDryRunRequest):
    return SkillDryRunService().dry_run(request).model_dump()


@router.post("/compose")
def compose_skills(payload: dict[str, Any] = Body(...)):
    return SkillComposerService().compose([str(item) for item in payload.get("skill_ids", [])]).model_dump()


@router.post("/output/validate")
def validate_skill_output(payload: dict[str, Any] = Body(...)):
    return SkillOutputValidator().validate(str(payload.get("skill_id", "")), dict(payload.get("output", {}))).model_dump()


@router.get("/traces/{trace_id}")
def get_skill_trace(trace_id: str):
    trace = SkillTraceService().get(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="skill_trace_not_found")
    return {"status": "ok", "trace": trace}
