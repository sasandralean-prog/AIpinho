from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.vision.contracts import DocumentReadRequest, OCRRequest
from aipinho.services.vision.document_image_reader_service import DocumentImageReaderService
from aipinho.services.vision.ocr_pipeline_service import OCRPipelineService

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


@router.get("/status")
def get_status() -> dict[str, object]:
    return OCRPipelineService().status()


@router.post("/extract")
def extract_ocr(request: OCRRequest) -> dict[str, object]:
    result = OCRPipelineService().extract(request)
    return {"status": result.status, "run_id": result.run_id, "result": result.model_dump()}


@router.post("/document/read")
def read_document(request: DocumentReadRequest) -> dict[str, object]:
    result = DocumentImageReaderService().read(request)
    return {"status": result.status, "run_id": result.run_id, "result": result.model_dump()}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    run = OCRPipelineService().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="ocr_run_not_found")
    return {"status": run.get("status", "ok"), "run": run}
