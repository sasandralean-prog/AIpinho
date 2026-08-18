from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.patching.quality.patch_quality_gate_request import PatchQualityGateRequest
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService

router = APIRouter(prefix="/api/v1/patch-quality", tags=["patch-quality"])


@router.get("/status")
def patch_quality_status() -> dict[str, object]:
    return {"status": "ok", "patch_quality": PatchQualityGateService().status()}


@router.post("/validate-plan/{plan_id}")
def validate_plan(plan_id: str) -> dict[str, object]:
    result = PatchQualityGateService().validate_plan(plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="patch_plan_not_found")
    return {"status": result.status, "quality": result}


@router.post("/validate-diff")
def validate_diff(request: PatchQualityGateRequest) -> dict[str, object]:
    result = PatchQualityGateService().validate_diff(request)
    return {"status": result.status, "quality": result}


@router.post("/validate-static")
def validate_static(request: PatchQualityGateRequest) -> dict[str, object]:
    result = PatchQualityGateService().validate_static(request)
    return {"status": result.status, "quality": result}


@router.post("/validate-plan/{plan_id}/refresh")
def refresh_plan_quality(plan_id: str) -> dict[str, object]:
    result = PatchQualityGateService().refresh_plan(plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="patch_plan_not_found")
    return {"status": result.status, "quality": result}


@router.get("/results/{quality_id}")
def get_result(quality_id: str) -> dict[str, object]:
    result = PatchQualityGateService().get_result(quality_id)
    if result is None:
        raise HTTPException(status_code=404, detail="patch_quality_not_found")
    return {"status": result.status, "quality": result}


@router.get("/results/{quality_id}/trace")
def get_result_trace(quality_id: str) -> dict[str, object]:
    trace = PatchQualityGateService().get_trace(quality_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="patch_quality_trace_not_found")
    return {"status": "ok", "trace": trace}


@router.get("/results")
def list_results(plan_id: str | None = None, status: str | None = None, limit: int = 100) -> dict[str, object]:
    return {"status": "ok", "results": PatchQualityGateService().list_results(plan_id=plan_id, status=status, limit=limit)}
