from __future__ import annotations

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class EventClient(BaseClient):
    def list_events(self, limit: int = 100) -> ApiResult: return self.get(f"/api/v1/events?limit={limit}")
    def detail(self, event_id: str) -> ApiResult: return self.get(f"/api/v1/events/{event_id}")
    def raw(self, event_id: str) -> ApiResult: return self.get(f"/api/v1/events/{event_id}/raw")
    def since(self, cursor: str) -> ApiResult: return self.get(f"/api/v1/realtime/events/since/{cursor}")
    def displayable(self, event: dict[str, object], known_contracts: set[str]) -> bool:
        return str(event.get("event_type")) in known_contracts and str(event.get("visibility", "public")) not in {"hidden", "internal"}
