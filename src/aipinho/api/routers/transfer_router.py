from __future__ import annotations
from fastapi import APIRouter, HTTPException
from aipinho.services.transfers.download_job_service import DownloadJobService
from aipinho.services.transfers.transfer_integrity_service import TransferIntegrityService
from aipinho.services.transfers.upload_job_service import UploadJobService
router=APIRouter(prefix="/api/v1/transfers",tags=["transfers"])
@router.post("/downloads")
def create_download(payload:dict[str,object])->dict[str,object]:
    try: return DownloadJobService().create(str(payload.get("artifact_id") or ""),filename=payload.get("filename") if isinstance(payload.get("filename"),str) else None,expected_sha256=payload.get("expected_sha256") if isinstance(payload.get("expected_sha256"),str) else None).model_dump()
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
@router.get("/downloads/{job_id}")
def get_download(job_id:str)->dict[str,object]:
    job=DownloadJobService().get(job_id)
    if job is None: raise HTTPException(status_code=404,detail="download_job_not_found")
    return job.model_dump()
@router.post("/downloads/{job_id}/retry")
def retry_download(job_id:str)->dict[str,object]:
    try: return DownloadJobService().retry(job_id).model_dump()
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail="download_job_not_found") from exc
@router.post("/uploads")
def create_upload(payload:dict[str,object])->dict[str,object]:
    try: return UploadJobService().create(str(payload.get("filename") or ""),size_bytes=int(payload.get("size_bytes") or 0),content_type=payload.get("content_type") if isinstance(payload.get("content_type"),str) else None).model_dump()
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
@router.get("/uploads/{job_id}")
def get_upload(job_id:str)->dict[str,object]:
    job=UploadJobService().get(job_id)
    if job is None: raise HTTPException(status_code=404,detail="upload_job_not_found")
    return job.model_dump()
@router.post("/uploads/{job_id}/retry")
def retry_upload(job_id:str)->dict[str,object]:
    try: return UploadJobService().retry(job_id).model_dump()
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail="upload_job_not_found") from exc
@router.get("/{job_id}/integrity")
def transfer_integrity(job_id:str,expected_sha256:str|None=None,actual_sha256:str|None=None)->dict[str,object]: return TransferIntegrityService().verify(job_id=job_id,expected_sha256=expected_sha256,actual_sha256=actual_sha256).model_dump()
