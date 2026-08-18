from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.models.model_doctor_request import ModelDoctorRequest
from aipinho.services.debugger.debug_trace_service import DebugTraceService
from aipinho.services.models.model_doctor_service import ModelDoctorService

router = APIRouter(prefix="/api/v1/models", tags=["model-doctor"])


@router.post("/{model_id}/doctor")
def run_model_doctor(model_id: str, request: ModelDoctorRequest | None = None) -> dict[str, object]:
    result = ModelDoctorService().run_for_model(model_id, request or ModelDoctorRequest())
    if result is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    return {"status": "ok", "result": result.model_dump()}


@router.post("/doctor/all")
def run_all_model_doctors(request: ModelDoctorRequest | None = None) -> dict[str, object]:
    results = ModelDoctorService().run_all(request or ModelDoctorRequest())
    return {"status": "ok", "results": [result.model_dump() for result in results], "count": len(results)}


@router.get("/doctor/report")
def get_model_doctor_report() -> dict[str, object]:
    return ModelDoctorService().latest_report()


@router.get("/doctor/results/{doctor_run_id}")
def get_model_doctor_result(doctor_run_id: str) -> dict[str, object]:
    result = ModelDoctorService().get_result(doctor_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="doctor_result_not_found")
    return {"status": "ok", "result": result}


@router.get("/doctor/results/{doctor_run_id}/trace")
def get_model_doctor_trace(doctor_run_id: str) -> dict[str, object]:
    result = ModelDoctorService().get_result(doctor_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="doctor_result_not_found")
    trace_id = result.get("trace_id")
    if not trace_id:
        return {"status": "missing", "trace": None}
    return {"status": "ok", "trace_id": trace_id, "trace": DebugTraceService().get_trace(str(trace_id))}
