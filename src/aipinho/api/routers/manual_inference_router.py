from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.services.models.llama_smoke_test_service import LlamaSmokeTestService
from aipinho.services.models.manual_inference_profile_service import ManualInferenceProfileService
from aipinho.services.models.manual_inference_status_service import ManualInferenceStatusService
from aipinho.services.models.real_inference_run_store import RealInferenceRunStore

router = APIRouter(prefix="/api/v1/models/manual-inference", tags=["manual-inference"])


@router.get("/status")
def get_manual_inference_status() -> dict[str, object]:
    return ManualInferenceStatusService().status().model_dump()


@router.get("/profiles")
def get_manual_inference_profiles() -> dict[str, object]:
    service = ManualInferenceProfileService()
    return {"status": "ok", "profiles": service.list_profiles()}


@router.post("/validate")
def validate_manual_inference(request: ManualInferenceRequest) -> dict[str, object]:
    return LlamaSmokeTestService().validate(request)


@router.post("/smoke-preview")
def preview_manual_smoke(request: ManualInferenceRequest) -> dict[str, object]:
    return LlamaSmokeTestService().preview(request)


@router.post("/smoke-test")
def run_manual_smoke(request: ManualInferenceRequest) -> dict[str, object]:
    result = LlamaSmokeTestService().smoke_test(request)
    return {"status": result.status, "result": result.model_dump()}


@router.get("/runs/{run_id}")
def get_manual_inference_run(run_id: str) -> dict[str, object]:
    run = RealInferenceRunStore().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"status": "ok", "run": run}


@router.get("/runs/{run_id}/events")
def get_manual_inference_run_events(run_id: str) -> dict[str, object]:
    return {"status": "ok", "run_id": run_id, "events": RealInferenceRunStore().list_events(run_id)}
