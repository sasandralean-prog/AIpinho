from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.services.maintenance.maintenance_core import MaintenancePlaneService, MaintenanceRunService, MaintenanceTraceService

router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance"])


@router.get("/status")
def maintenance_status() -> dict[str, object]:
    return MaintenancePlaneService().status().model_dump()


@router.get("/runs")
def maintenance_runs() -> dict[str, object]:
    runs = MaintenanceRunService().list()
    return {"status": "ok", "count": len(runs), "runs": [item.model_dump() for item in runs]}


@router.get("/runs/{run_id}/trace")
def maintenance_run_trace(run_id: str) -> dict[str, object]:
    run = MaintenanceRunService().get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="maintenance_run_not_found")
    trace = MaintenanceTraceService().get_for_run(run)
    if trace is None:
        raise HTTPException(status_code=404, detail="maintenance_trace_not_found")
    return {"status": "ok", "trace": trace.model_dump()}


@router.get("/runs/{run_id}/violations")
def maintenance_run_violations(run_id: str) -> dict[str, object]:
    run = MaintenanceRunService().get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="maintenance_run_not_found")
    return {"status": "ok", "violations": [item.model_dump() for item in run.violations]}


@router.get("/runs/{run_id}")
def maintenance_run(run_id: str) -> dict[str, object]:
    run = MaintenanceRunService().get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="maintenance_run_not_found")
    return {"status": "ok", "run": run.model_dump()}
