from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.validation.validation_request import ValidationRequest
from aipinho.services.validation.validation_gate_service import ValidationGateService

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])
service = ValidationGateService()

@router.get("/status")
def get_validation_status() -> dict[str, object]:
    return service.status()

@router.post("/task-run/{run_id}")
def validate_task_run(run_id: str):
    result = service.validate_task_run_id(run_id)
    return result

@router.post("/task-result")
def validate_task_result(request: ValidationRequest):
    return service.validate_task_result_payload(request.payload)

@router.post("/report")
def validate_report(request: ValidationRequest):
    return service.validate_report_payload(request.payload, target_id=request.target_id)

@router.post("/report/{report_id}")
def validate_report_by_id(report_id: str):
    return service.validate_report_id(report_id)

@router.post("/role-pipeline/{run_id}")
def validate_role_pipeline(run_id: str):
    return service.validate_role_pipeline_id(run_id)

@router.post("/side-effects")
def validate_side_effects(request: ValidationRequest):
    return service.validate_side_effects(request.payload)

@router.post("/evidence")
def validate_evidence(request: ValidationRequest):
    return service.validate_evidence(request.payload)

@router.post("/context-usage")
def validate_context_usage(request: ValidationRequest):
    return service.validate_context_usage(request.payload)

@router.post("")
def validate_any(request: ValidationRequest):
    return service.validate_request(request)

@router.get("/results/{validation_id}")
def get_validation_result(validation_id: str):
    result = service.get_result(validation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="validation_result_not_found")
    return result

@router.get("/results/{validation_id}/trace")
def get_validation_trace(validation_id: str):
    trace = service.get_trace(validation_id)
    if not trace:
        raise HTTPException(status_code=404, detail="validation_trace_not_found")
    return {"validation_id": validation_id, "trace": trace}
