from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from aipinho.schemas.skills.skill_packs import SkillPackExecutionRequest, SkillPackSelectionRequest
from aipinho.services.skills.skill_pack_registry_service import (
    SkillPackExecutionService,
    SkillPackRegistry,
    SkillPackValidator,
)

router = APIRouter(prefix="/api/v1/skill-packs", tags=["skill-packs"])
mobile_router = APIRouter(prefix="/api/v1/mobile/view-model", tags=["mobile-skill-packs"])


@router.get("")
def list_skill_packs(
    category: str | None = None,
    agent_id: str | None = None,
    project_stack: str | None = None,
    include_archived: bool = False,
):
    registry = SkillPackRegistry()
    return {
        "status": "ok",
        "packs": [
            item.model_dump()
            for item in registry.list_packs(
                category=category,
                agent_id=agent_id,
                project_stack=project_stack,
                include_archived=include_archived,
            )
        ],
    }


@router.get("/health")
def skill_pack_health():
    return SkillPackRegistry().health()


@router.get("/status")
def skill_pack_status():
    return {"status": "ok", "registry": SkillPackRegistry().status().model_dump()}


@router.post("/select")
def select_skill_pack(request: SkillPackSelectionRequest):
    return SkillPackRegistry().select(request).model_dump()


@router.post("/validate")
def validate_skill_pack(payload: dict[str, Any] = Body(...)):
    return SkillPackValidator().validate(payload).model_dump()


@router.post("/{skill_pack_id}/execute")
def execute_skill_pack(skill_pack_id: str, request: SkillPackExecutionRequest):
    if request.skill_pack_id != skill_pack_id:
        raise HTTPException(status_code=400, detail="skill_pack_id_mismatch")
    return SkillPackExecutionService().execute(request).model_dump()


@router.get("/executions/{skill_pack_execution_id}")
def get_skill_pack_execution(skill_pack_execution_id: str):
    result = SkillPackExecutionService().get(skill_pack_execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="skill_pack_execution_not_found")
    return {"status": "ok", "skill_pack_execution": result.model_dump()}


@router.get("/executions/{skill_pack_execution_id}/trace")
def get_skill_pack_execution_trace(skill_pack_execution_id: str):
    trace = SkillPackExecutionService().trace(skill_pack_execution_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="skill_pack_execution_not_found")
    return trace


@router.get("/{skill_pack_id}")
def get_skill_pack(skill_pack_id: str):
    try:
        pack = SkillPackRegistry().get(skill_pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="skill_pack_not_found") from exc
    validation = SkillPackRegistry().validate_pack(pack)
    return {"status": "ok", "pack": pack.model_dump(), "validation": validation.model_dump()}


@router.get("/{skill_pack_id}/debugger")
def get_skill_pack_debugger(skill_pack_id: str):
    try:
        pack = SkillPackRegistry().get(skill_pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="skill_pack_not_found") from exc
    validation = SkillPackRegistry().validate_pack(pack)
    return {
        "status": "ok",
        "raw_default_visible": False,
        "skill_pack_id": skill_pack_id,
        "pack": pack.model_dump(),
        "validation": validation.model_dump(),
        "filters": {
            "skill_pack_id": skill_pack_id,
            "skill_ids": pack.included_skills,
            "category": pack.category,
            "agents": pack.supported_agents,
        },
    }


@router.get("/dashboard/summary")
def skill_pack_dashboard():
    registry = SkillPackRegistry()
    health = registry.health()
    packs = health.get("packs", [])
    return {
        "status": "ok",
        "active_packs": len([item for item in packs if item.get("status") == "active"]),
        "invalid_packs": len([item for item in packs if item.get("health_status") == "invalid"]),
        "degraded_packs": len([item for item in packs if item.get("health_status") == "degraded"]),
        "packs": packs,
    }


@mobile_router.get("/skill-packs")
def mobile_skill_packs_view_model():
    return SkillPackRegistry().mobile_view_model()
