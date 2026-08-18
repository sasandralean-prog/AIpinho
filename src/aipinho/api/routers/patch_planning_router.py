from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.patching.patch_plan_request import PatchPlanRequest
from aipinho.schemas.patching.model_patch_proposal import ModelAssistedPatchPlanRequest
from aipinho.services.patching.model_assisted_patch_planner_service import ModelAssistedPatchPlannerService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService

router = APIRouter(prefix="/api/v1/patch-plans", tags=["patch-plans"])


@router.get("/status")
def patch_planning_status() -> dict[str, object]:
    return {"status": "ok", "patch_planning": PatchPlanningService().status()}


@router.post("")
def create_patch_plan(request: PatchPlanRequest) -> dict[str, object]:
    result = PatchPlanningService().create_plan(request)
    return {"status": result.status, "plan": result.plan, "apply_enabled": result.apply_enabled, "write_enabled": result.write_enabled}


@router.post("/model-assisted")
def create_model_assisted_patch_plan(request: ModelAssistedPatchPlanRequest) -> dict[str, object]:
    result = ModelAssistedPatchPlannerService().create_plan(
        workspace=request.workspace,
        objective=request.objective,
        source_id=request.source_id,
        file_context_bundle=request.file_context_bundle,
        include_trace=request.include_trace,
    )
    return result.model_dump()


@router.post("/from-report/{report_id}")
def create_patch_plan_from_report(report_id: str, request: PatchPlanRequest) -> dict[str, object]:
    return create_patch_plan(request.model_copy(update={"source_type": "project_report", "source_id": report_id}))


@router.post("/from-task-run/{run_id}")
def create_patch_plan_from_task_run(run_id: str, request: PatchPlanRequest) -> dict[str, object]:
    return create_patch_plan(request.model_copy(update={"source_type": "task_run_result", "source_id": run_id}))


@router.post("/from-validation/{validation_id}")
def create_patch_plan_from_validation(validation_id: str, request: PatchPlanRequest) -> dict[str, object]:
    return create_patch_plan(request.model_copy(update={"source_type": "validation_result", "source_id": validation_id}))


@router.post("/{plan_id}/refresh")
def refresh_patch_plan(plan_id: str) -> dict[str, object]:
    plan = PatchPlanningService().refresh(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="patch_plan_not_found")
    return {"status": plan.status, "plan": plan}


@router.post("/{plan_id}/validate")
def validate_patch_plan(plan_id: str) -> dict[str, object]:
    validation = PatchPlanningService().validate_plan(plan_id)
    if validation is None:
        raise HTTPException(status_code=404, detail="patch_plan_not_found")
    return {"status": validation.status, "validation": validation}


@router.get("/{plan_id}")
def get_patch_plan(plan_id: str) -> dict[str, object]:
    plan = PatchPlanningService().get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="patch_plan_not_found")
    return {"status": plan.status, "plan": plan}


@router.get("/{plan_id}/diff")
def get_patch_plan_diff(plan_id: str) -> dict[str, object]:
    service = PatchPlanningService()
    diff = service.get_diff(plan_id)
    if diff is None:
        raise HTTPException(status_code=404, detail="patch_diff_not_found")
    plan = service.get_plan(plan_id)
    return {"status": diff.status, "diff": diff, "apply_enabled": bool(plan.apply_enabled) if plan else False, "write_enabled": bool(plan.write_enabled) if plan else False}


@router.get("/{plan_id}/evidence")
def get_patch_plan_evidence(plan_id: str) -> dict[str, object]:
    return {"status": "ok", "evidence": PatchPlanningService().get_evidence(plan_id)}


@router.get("/{plan_id}/risk")
def get_patch_plan_risk(plan_id: str) -> dict[str, object]:
    risk = PatchPlanningService().get_risk(plan_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="patch_risk_not_found")
    return {"status": "ok", "risk": risk}


@router.get("/{plan_id}/quality")
def get_patch_plan_quality(plan_id: str) -> dict[str, object]:
    result = PatchQualityGateService().get_latest_for_plan(plan_id)
    if result is None:
        plan = PatchPlanningService().get_plan(plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="patch_plan_not_found")
        return {"status": "not_validated", "quality_gate": plan.quality_gate}
    return {"status": result.status, "quality": result}


@router.get("/{plan_id}/apply-status")
def get_patch_plan_apply_status(plan_id: str) -> dict[str, object]:
    plan = PatchPlanningService().get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="patch_plan_not_found")
    return PatchApplyService().apply_status_for_plan(plan_id)


@router.get("/{plan_id}/trace")
def get_patch_plan_trace(plan_id: str) -> dict[str, object]:
    return {"status": "ok", "trace": PatchPlanningService().get_trace(plan_id)}


@router.get("")
def list_patch_plans(status: str | None = None, risk_level: str | None = None, source_type: str | None = None, workspace: str | None = None, limit: int = 100) -> dict[str, object]:
    return {"status": "ok", "plans": PatchPlanningService().list_plans(status=status, risk_level=risk_level, source_type=source_type, workspace=workspace, limit=limit)}
