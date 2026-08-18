from __future__ import annotations

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class EventContractClient(BaseClient):
    def status(self) -> ApiResult: return self.get("/api/v1/events/status")
    def contracts(self) -> ApiResult: return self.get("/api/v1/events/contracts")
    def contract(self, event_type: str) -> ApiResult: return self.get(f"/api/v1/events/contracts/{event_type}")
    def ownership(self) -> ApiResult: return self.get("/api/v1/policy/ownership")
