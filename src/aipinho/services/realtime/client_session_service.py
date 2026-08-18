from __future__ import annotations
from uuid import uuid4
class ClientSessionService:
    def create(self) -> dict[str, object]:
        return {"status": "ok", "client_session_id": f"realtime_client_{uuid4().hex}"}
