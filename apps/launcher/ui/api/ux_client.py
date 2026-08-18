from __future__ import annotations
from apps.launcher.ui.api.base_client import ApiResult, BaseClient
class UXClient(BaseClient):
    def status(self)->ApiResult: return self.get("/api/v1/ux/status")
    def health(self)->ApiResult: return self.get("/api/v1/ux/health")
    def notifications(self)->ApiResult: return self.get("/api/v1/ux/notifications")
    def ack_notifications(self,notification_ids:list[str])->ApiResult: return self.post("/api/v1/ux/notifications/ack",{"notification_ids":notification_ids})
    def session_recovery(self)->ApiResult: return self.get("/api/v1/session/recovery")
    def restore_session(self,payload:dict[str,object])->ApiResult: return self.post("/api/v1/session/recovery/restore",payload)
