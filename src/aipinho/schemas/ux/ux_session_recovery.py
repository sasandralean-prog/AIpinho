from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXSessionRecovery(AIpinhoModel):
    session_id: str | None = None
    cursor: str = "0"
    draft: str = ""
    last_snapshot: dict[str, object] | None = None
    stale: bool = False
