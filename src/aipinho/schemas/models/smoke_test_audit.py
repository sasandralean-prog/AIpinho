from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class SmokeTestAuditEvent(AIpinhoModel):
    audit_event_id: str = Field(default_factory=lambda: f"audit_{uuid4().hex}")
    run_id: str
    profile_id: str
    provider_id: str
    model_id: str
    real_inference: bool = False
    process_started: bool = False
    status: str
    duration_ms: int = 0
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
