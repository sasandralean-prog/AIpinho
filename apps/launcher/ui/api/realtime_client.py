from __future__ import annotations

import json
from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class RealtimeClient(BaseClient):
    def status(self) -> ApiResult: return self.get("/api/v1/realtime/status")
    def since(self, cursor: str) -> ApiResult: return self.get(f"/api/v1/realtime/events/since/{cursor}")
    def parse_sse(self, text: str) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        for block in text.split("\n\n"):
            data_lines = [line[5:].strip() for line in block.splitlines() if line.startswith("data:")]
            for raw in data_lines:
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    events.append({"raw": raw, "status": "degraded"})
        return events
