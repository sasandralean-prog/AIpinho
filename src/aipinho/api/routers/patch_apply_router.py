from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.patching.apply.patch_apply_request import PatchApplyRequest
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService

router = APIRouter(prefix="/api/v1/patch-apply", tags=["patch-apply"])


@router.get("/status")
def patch_apply_status() -> dict[str, object]:
    return {"status": "ok", "patch_apply": PatchApplyService().status()}


@router.post("/request-approval/{plan_id}")
def request_patch_apply_approval(plan_id: str) -> dict[str, object]:
    try:
        approval = PatchApplyService().request_approval(plan_id)
        return {"status": "ok", "approval": approval, "applied": False}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/runs/from-plan/{plan_id}")
def create_apply_run(plan_id: str, request: PatchApplyRequest) -> dict[str, object]:
    run = PatchApplyService().create_run_from_plan(plan_id, request)
    return {"status": run.status, "run": run, "applied": False}


@router.post("/runs/{apply_run_id}/execute")
def execute_apply_run(apply_run_id: str) -> dict[str, object]:
    result = PatchApplyService().execute(apply_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="patch_apply_run_not_found")
    return {"status": result.status, "result": result}


@router.post("/runs/{apply_run_id}/cancel")
def cancel_apply_run(apply_run_id: str) -> dict[str, object]:
    run = PatchApplyService().cancel(apply_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="patch_apply_run_not_found")
    return {"status": run.status, "run": run}


@router.post("/runs/{apply_run_id}/rollback")
def rollback_apply_run(apply_run_id: str) -> dict[str, object]:
    rollback = PatchApplyService().rollback(apply_run_id)
    if rollback is None:
        raise HTTPException(status_code=404, detail="patch_apply_run_not_found")
    return {"status": rollback.status, "rollback": rollback}


@router.get("/runs/{apply_run_id}")
def get_apply_run(apply_run_id: str) -> dict[str, object]:
    run = PatchApplyService().get_run(apply_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="patch_apply_run_not_found")
    return {"status": run.status, "run": run}


@router.get("/runs/{apply_run_id}/events")
def get_apply_run_events(apply_run_id: str) -> dict[str, object]:
    service = PatchApplyService()
    if service.get_run(apply_run_id) is None:
        raise HTTPException(status_code=404, detail="patch_apply_run_not_found")
    return {"status": "ok", "events": service.get_events(apply_run_id)}


@router.get("/runs/{apply_run_id}/trace")
def get_apply_run_trace(apply_run_id: str) -> dict[str, object]:
    trace = PatchApplyService().get_trace(apply_run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="patch_apply_trace_not_found")
    return {"status": "ok", "trace": trace}


@router.get("/runs/{apply_run_id}/result")
def get_apply_run_result(apply_run_id: str) -> dict[str, object]:
    result = PatchApplyService().get_result(apply_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="patch_apply_result_not_found")
    return {"status": result.status, "result": result}


@router.get("/runs")
def list_apply_runs(plan_id: str | None = None, approval_id: str | None = None, status: str | None = None, limit: int = 100) -> dict[str, object]:
    return {"status": "ok", "runs": PatchApplyService().list_runs(plan_id=plan_id, approval_id=approval_id, status=status, limit=limit)}
