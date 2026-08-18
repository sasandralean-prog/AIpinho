from __future__ import annotations

from apps.launcher.ui.api.base_client import ApiResult, BaseClient


class AgentMarketplaceClient(BaseClient):
    def status(self) -> ApiResult:
        return self.get("/api/v1/agent-marketplace/status")

    def snapshot(self) -> ApiResult:
        return self.get("/api/v1/agent-marketplace/snapshot")

    def query_capability(self, capability_id: str) -> ApiResult:
        return self.get(f"/api/v1/agent-marketplace/capabilities/{capability_id}")

    def heartbeat(self, agent_id: str, status: str = "online") -> ApiResult:
        return self.post(
            f"/api/v1/agent-marketplace/agents/{agent_id}/heartbeat",
            {
                "agent_id": agent_id,
                "status": status,
                "available": status == "online",
            },
        )
