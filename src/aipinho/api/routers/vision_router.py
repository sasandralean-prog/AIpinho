from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.vision.contracts import OCRRequest, UIInspectionRequest, VisionAnalysisRequest
from aipinho.services.vision.ocr_pipeline_service import OCRPipelineService
from aipinho.services.vision.diagram_analysis_service import DiagramAnalysisService
from aipinho.services.vision.ui_inspection_service import UIInspectionService
from aipinho.services.vision.vision_analysis_service import VisionAnalysisService
from aipinho.services.vision.vision_status_service import VisionStatusService
from aipinho.services.vision.vision_trace_service import VisionTraceService

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


@router.get("/status")
def get_status() -> dict[str, object]:
    return VisionStatusService().status()


@router.post("/analyze")
def analyze_image(request: VisionAnalysisRequest) -> dict[str, object]:
    result = VisionAnalysisService().analyze(request)
    return {"status": result.status, "run_id": result.run_id, "result": result.model_dump()}


@router.post("/ocr")
def analyze_ocr(request: OCRRequest) -> dict[str, object]:
    result = OCRPipelineService().extract(request)
    return {"status": result.status, "run_id": result.run_id, "result": result.model_dump()}


@router.post("/ui-inspect")
def inspect_ui(request: UIInspectionRequest) -> dict[str, object]:
    result = UIInspectionService().inspect(request)
    return {"status": result.status, "run_id": result.run_id, "result": result.model_dump()}


@router.post("/diagram/analyze")
def analyze_diagram(request: VisionAnalysisRequest) -> dict[str, object]:
    result = DiagramAnalysisService().analyze(request)
    return {"status": result.status, "run_id": result.run_id, "result": result.model_dump()}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    run = VisionAnalysisService().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="vision_run_not_found")
    return {"status": run.get("status", "ok"), "run": run}


@router.get("/traces/{trace_id}")
def get_trace(trace_id: str) -> dict[str, object]:
    trace = VisionTraceService().get(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="vision_trace_not_found")
    return {"status": "ok", "trace": trace}
