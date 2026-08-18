from __future__ import annotations
from urllib.parse import quote
from apps.launcher.ui.api.base_client import ApiResult, BaseClient
class RawClient(BaseClient):
    def viewer(self,raw_ref_id:str)->ApiResult: return self.get(f"/api/v1/raw/{raw_ref_id}/viewer")
    def search(self,raw_ref_id:str,query:str)->ApiResult: return self.get(f"/api/v1/raw/{raw_ref_id}/search?query={quote(query)}")
    def copy(self,raw_ref_id:str)->ApiResult: return self.get(f"/api/v1/raw/{raw_ref_id}/copy")
