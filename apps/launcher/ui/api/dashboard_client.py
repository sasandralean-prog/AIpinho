from __future__ import annotations

from apps.launcher.ui.api.base_client import ApiResult, BaseClient


class DashboardClient(BaseClient):
    def multi_agent(self) -> ApiResult:
        return self.get("/api/v1/dashboard/multi-agent")

    def health(self) -> ApiResult:
        return self.get("/api/v1/dashboard/health")

    def state_consistency(self) -> ApiResult:
        return self.get("/api/v1/dashboard/state-consistency")
