from __future__ import annotations
import json
class EventStreamService:
    def status_event(self) -> str:
        return "event: service_status_changed\ndata: " + json.dumps({"status": "ok", "port": 9089}) + "\n\n"
