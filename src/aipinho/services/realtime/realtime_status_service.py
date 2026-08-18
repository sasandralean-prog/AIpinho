from __future__ import annotations
from datetime import datetime, timezone

class RealtimeStatusService:
    def status(self) -> dict[str, object]:
        return {"status": "ok", "enabled": True, "port": 9089, "mode": "event_stream", "support_sse": True, "support_websocket_future": True, "require_token_auth": True}

class SyncHeartbeatService:
    def heartbeat(self) -> dict[str, object]:
        return {"status": "ok", "port": 9089, "heartbeat_at": datetime.now(timezone.utc).isoformat()}
