from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.workflows import (
    WorkflowCancelRequest,
    WorkflowPlanCreateRequest,
    WorkflowResumeRequest,
    WorkflowRunCreateRequest,
)
from aipinho.services.autopilot.workflow_v2_service import WorkflowExecutor, WorkflowPlanner, WorkflowStore


router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])
mobile_router = APIRouter(prefix="/api/v1/mobile/view-model", tags=["mobile-workflows"])


def _store() -> WorkflowStore:
    return WorkflowStore()


def _executor() -> WorkflowExecutor:
    return WorkflowExecutor(store=_store())


@router.post("/plans")
def create_workflow_plan(request: WorkflowPlanCreateRequest):
    return {"status": "ok", "workflow_plan": WorkflowPlanner(store=_store()).create_plan(request).model_dump()}


@router.get("/plans")
def list_workflow_plans():
    return {"status": "ok", "plans": [item.model_dump() for item in _store().list_plans()]}


@router.get("/plans/{workflow_plan_id}")
def get_workflow_plan(workflow_plan_id: str):
    plan = _store().get_plan(workflow_plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="workflow_plan_not_found")
    return {"status": "ok", "workflow_plan": plan.model_dump()}


@router.post("/runs")
def create_workflow_run(request: WorkflowRunCreateRequest):
    try:
        run = _executor().create_run(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_plan_not_found") from exc
    return {"status": "ok", "workflow_run": run.model_dump()}


@router.get("/runs")
def list_workflow_runs(include_all: bool = False):
    return {"status": "ok", "runs": [item.model_dump() for item in _store().list_runs(include_all=include_all)]}


@router.get("/runs/{workflow_run_id}")
def get_workflow_run(workflow_run_id: str):
    run = _store().get_run(workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return {"status": "ok", "workflow_run": run.model_dump()}


@router.post("/runs/{workflow_run_id}/pause")
def pause_workflow_run(workflow_run_id: str):
    try:
        return {"status": "ok", "workflow_run": _executor().pause(workflow_run_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_run_not_found") from exc


@router.post("/runs/{workflow_run_id}/resume")
def resume_workflow_run(workflow_run_id: str, request: WorkflowResumeRequest):
    try:
        return {"status": "ok", "workflow_run": _executor().resume(workflow_run_id, request).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_run_not_found") from exc


@router.post("/runs/{workflow_run_id}/cancel")
def cancel_workflow_run(workflow_run_id: str, request: WorkflowCancelRequest):
    try:
        return {"status": "ok", "workflow_run": _executor().cancel(workflow_run_id, request).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_run_not_found") from exc


@router.get("/runs/{workflow_run_id}/approvals")
def list_workflow_approvals(workflow_run_id: str):
    if _store().get_run(workflow_run_id) is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return {"status": "ok", "approvals": [item.model_dump() for item in _store().list_approvals(workflow_run_id=workflow_run_id)]}


@router.post("/runs/{workflow_run_id}/approvals/{approval_id}/approve")
def approve_workflow_run(workflow_run_id: str, approval_id: str):
    try:
        return {"status": "ok", "workflow_run": _executor().approve(workflow_run_id, approval_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_approval_not_found") from exc


@router.post("/runs/{workflow_run_id}/approvals/{approval_id}/reject")
def reject_workflow_run(workflow_run_id: str, approval_id: str):
    try:
        return {"status": "ok", "workflow_run": _executor().reject(workflow_run_id, approval_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_approval_not_found") from exc


@router.get("/runs/{workflow_run_id}/checkpoints")
def list_workflow_checkpoints(workflow_run_id: str):
    if _store().get_run(workflow_run_id) is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return {"status": "ok", "checkpoints": [item.model_dump() for item in _store().list_checkpoints(workflow_run_id=workflow_run_id)]}


@router.get("/checkpoints/{checkpoint_id}")
def get_workflow_checkpoint(checkpoint_id: str):
    checkpoint = _store().get_checkpoint(checkpoint_id)
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="workflow_checkpoint_not_found")
    return {"status": "ok", "checkpoint": checkpoint.model_dump()}


@router.post("/runs/{workflow_run_id}/recover")
def create_workflow_recovery(workflow_run_id: str):
    try:
        return {"status": "ok", "recovery_plan": _executor().recover(workflow_run_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_run_not_found") from exc


@router.get("/recovery/{recovery_plan_id}")
def get_workflow_recovery(recovery_plan_id: str):
    recovery = _store().get_recovery(recovery_plan_id)
    if recovery is None:
        raise HTTPException(status_code=404, detail="workflow_recovery_not_found")
    return {"status": "ok", "recovery_plan": recovery.model_dump()}


@router.post("/runs/{workflow_run_id}/report")
def create_workflow_report(workflow_run_id: str):
    try:
        return {"status": "ok", "report": _executor().report(workflow_run_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_run_not_found") from exc


@router.get("/runs/{workflow_run_id}/trace")
def get_workflow_trace(workflow_run_id: str):
    try:
        return _executor().trace(workflow_run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow_run_not_found") from exc


@router.get("/runs/{workflow_run_id}/step-results")
def list_workflow_step_results(workflow_run_id: str):
    if _store().get_run(workflow_run_id) is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return {
        "status": "ok",
        "step_results": [item.model_dump() for item in _store().list_step_results(workflow_run_id=workflow_run_id)],
    }


@router.get("/runs/{workflow_run_id}/replay")
def list_workflow_replays(workflow_run_id: str):
    if _store().get_run(workflow_run_id) is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return {
        "status": "ok",
        "replays": [item.model_dump() for item in _store().list_replays(workflow_run_id=workflow_run_id)],
    }


@mobile_router.get("/workflows")
def mobile_workflows_view_model():
    return _executor().mobile_view_model()
