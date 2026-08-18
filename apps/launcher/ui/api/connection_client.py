from __future__ import annotations

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class ConnectionClient(BaseClient):
    def profiles(self) -> ApiResult: return self.get("/api/v1/connection/profiles")
    def select_profile(self, profile_id: str, host: str | None = None) -> ApiResult: return self.post("/api/v1/connection/profiles/select", {"profile_id": profile_id, "host": host})
    def adb_commands(self) -> ApiResult: return self.get("/api/v1/connection/adb/reverse-commands")
    def test_connection(self) -> ApiResult: return self.post("/api/v1/connection/test", {})
    def pairing_status(self) -> ApiResult: return self.get("/api/v1/mobile/pairing/status")
    def create_token(self) -> ApiResult: return self.post("/api/v1/mobile/pairing/create-token", {})
