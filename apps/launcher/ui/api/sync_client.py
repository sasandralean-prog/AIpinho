from __future__ import annotations

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class SyncClient(BaseClient):
    def snapshot(self) -> ApiResult: return self.get("/api/v1/sync/snapshot")
    def changes(self, cursor: str | None = None) -> ApiResult:
        suffix = f"?cursor={cursor}" if cursor else ""
        return self.get(f"/api/v1/sync/changes{suffix}")
