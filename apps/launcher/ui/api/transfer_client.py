from __future__ import annotations
from apps.launcher.ui.api.base_client import ApiResult, BaseClient
class TransferClient(BaseClient):
    def create_download(self,artifact_id:str,filename:str|None=None,expected_sha256:str|None=None)->ApiResult: return self.post("/api/v1/transfers/downloads",{"artifact_id":artifact_id,"filename":filename,"expected_sha256":expected_sha256})
    def download_status(self,job_id:str)->ApiResult: return self.get(f"/api/v1/transfers/downloads/{job_id}")
    def retry_download(self,job_id:str)->ApiResult: return self.post(f"/api/v1/transfers/downloads/{job_id}/retry")
    def create_upload(self,filename:str,size_bytes:int=0,content_type:str|None=None)->ApiResult: return self.post("/api/v1/transfers/uploads",{"filename":filename,"size_bytes":size_bytes,"content_type":content_type})
    def upload_status(self,job_id:str)->ApiResult: return self.get(f"/api/v1/transfers/uploads/{job_id}")
    def retry_upload(self,job_id:str)->ApiResult: return self.post(f"/api/v1/transfers/uploads/{job_id}/retry")
