from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.artifacts.artifact_write_request import ArtifactWriteRequest
from aipinho.services.artifacts.artifact_write_execution_service import ArtifactWriteExecutionService

router = APIRouter(prefix="/api/v1/artifacts/write", tags=["artifact-write"])


def _controlled_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


@router.get("/status")
def artifact_write_status() -> dict[str, object]:
    return {"status": "ok", "artifact_write": ArtifactWriteExecutionService().status()}


@router.post("/from-preview/{preview_id}")
def create_write_run_from_preview(preview_id: str, request: ArtifactWriteRequest) -> dict[str, object]:
    try:
        return {"status": "ok", "write_run": ArtifactWriteExecutionService().create_run_from_preview(preview_id, request)}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/{write_run_id}/execute")
def execute_write_run(write_run_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "result": ArtifactWriteExecutionService().execute(write_run_id)}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/{write_run_id}/cancel")
def cancel_write_run(write_run_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "write_run": ArtifactWriteExecutionService().cancel(write_run_id)}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.get("/runs/{write_run_id}")
def get_write_run(write_run_id: str) -> dict[str, object]:
    run = ArtifactWriteExecutionService().get_run(write_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="artifact_write_run_not_found")
    return {"status": "ok", "write_run": run}


@router.get("/runs/{write_run_id}/events")
def get_write_run_events(write_run_id: str) -> dict[str, object]:
    return {"status": "ok", "events": ArtifactWriteExecutionService().get_events(write_run_id)}


@router.get("/runs/{write_run_id}/trace")
def get_write_run_trace(write_run_id: str) -> dict[str, object]:
    return {"status": "ok", "trace": ArtifactWriteExecutionService().get_trace(write_run_id)}


@router.get("/runs/{write_run_id}/result")
def get_write_run_result(write_run_id: str) -> dict[str, object]:
    result = ArtifactWriteExecutionService().get_result(write_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="artifact_write_result_not_found")
    return {"status": "ok", "result": result}


@router.get("/runs")
def list_write_runs(status: str | None = None, preview_id: str | None = None, approval_id: str | None = None, limit: int = 100) -> dict[str, object]:
    return {"status": "ok", "write_runs": ArtifactWriteExecutionService().list_runs(status=status, preview_id=preview_id, approval_id=approval_id, limit=limit)}
