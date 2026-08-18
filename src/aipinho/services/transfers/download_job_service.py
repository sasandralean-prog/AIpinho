from __future__ import annotations
from uuid import uuid4
from aipinho.schemas.transfers.download_job import DownloadJob
from aipinho.services.transfers.transfer_store import TransferStore
class DownloadJobService:
    def __init__(self): self.store=TransferStore("downloads")
    def create(self,artifact_id:str,filename:str|None=None,expected_sha256:str|None=None)->DownloadJob:
        if not artifact_id or any(sep in artifact_id for sep in ("/", "\\", ":")): raise ValueError("artifact_id_required")
        job=DownloadJob(job_id=f"download_{uuid4().hex}",artifact_id=artifact_id,filename=filename,expected_sha256=expected_sha256,status="queued"); self.store.save(job.job_id,job.model_dump()); return job
    def get(self,job_id:str)->DownloadJob|None:
        data=self.store.get(job_id); return DownloadJob(**data) if data else None
    def retry(self,job_id:str)->DownloadJob:
        job=self.get(job_id)
        if job is None: raise FileNotFoundError(job_id)
        job.status="retry_queued"; self.store.save(job.job_id,job.model_dump()); return job
