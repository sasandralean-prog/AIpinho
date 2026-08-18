from __future__ import annotations
from typing import Any
from aipinho.services.events.event_core import redact_payload


class SnapshotCollector:
    collector_type = "generic"
    def collect(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"collector_type": self.collector_type, "payload": redact_payload(payload or {}), "side_effects_performed": False}
