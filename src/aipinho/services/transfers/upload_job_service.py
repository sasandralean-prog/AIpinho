from __future__ import annotations
from pathlib import PurePath
from uuid import uuid4
from aipinho.schemas.transfers.upload_job import UploadJob
from aipinho.services.transfers.transfer_store import TransferStore
BLOCKED_EXTENSIONS={".exe",".dll",".bat",".cmd",".ps1",".sh",".msi"}
class UploadJobService:
    def __init__(self): self.store=TransferStore("uploads")
    def create(self,filename:str,size_bytes:int=0,content_type:str|None=None)->UploadJob:
        name=PurePath(filename).name
        if not name: raise ValueError("filename_required")
        if PurePath(name).suffix.lower() in BLOCKED_EXTENSIONS: raise ValueError("executable_upload_blocked")
        job=UploadJob(job_id=f"upload_{uuid4().hex}",filename=name,size_bytes=size_bytes,content_type=content_type,status="queued"); self.store.save(job.job_id,job.model_dump()); return job
    def get(self,job_id:str)->UploadJob|None:
        data=self.store.get(job_id); return UploadJob(**data) if data else None
    def retry(self,job_id:str)->UploadJob:
        job=self.get(job_id)
        if job is None: raise FileNotFoundError(job_id)
        job.status="retry_queued"; self.store.save(job.job_id,job.model_dump()); return job
