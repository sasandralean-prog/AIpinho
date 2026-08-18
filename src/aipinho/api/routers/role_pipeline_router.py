from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.roles.role_pipeline_run import RolePipelineRunRequest
from aipinho.services.roles.role_pipeline_service import RolePipelineService

router = APIRouter(prefix="/api/v1/role-pipelines", tags=["role-pipelines"])


@router.get("/status")
def get_role_pipeline_status() -> dict[str, object]:
    return RolePipelineService().status()


@router.get("")
def list_role_pipelines() -> dict[str, object]:
    return {"status": "ok", "pipelines": RolePipelineService().list_pipelines()}


@router.get("/{pipeline_id}")
def get_role_pipeline(pipeline_id: str) -> dict[str, object]:
    pipeline = RolePipelineService().get_pipeline(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="pipeline_not_found")
    return {"status": "ok", "pipeline": pipeline}


@router.post("/preview")
def preview_role_pipeline(request: RolePipelineRunRequest) -> dict[str, object]:
    run = RolePipelineService().preview_pipeline(request.model_copy(update={"mode": "preview"}))
    return {"status": run.status, "run": run, "model_invoked": False, "side_effects": False}


@router.post("/run")
def run_role_pipeline(request: RolePipelineRunRequest) -> dict[str, object]:
    run = RolePipelineService().run_pipeline(request.model_copy(update={"mode": "run"}))
    return {"status": run.status, "run": run, "real_inference": False, "side_effects": False}


@router.get("/runs/{run_id}")
def get_role_pipeline_run(run_id: str) -> dict[str, object]:
    run = RolePipelineService().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"status": "ok", "run": run}


@router.get("/runs/{run_id}/trace")
def get_role_pipeline_trace(run_id: str) -> dict[str, object]:
    trace = RolePipelineService().get_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="trace_not_found")
    return {"status": "ok", "run_id": run_id, "trace": trace}
