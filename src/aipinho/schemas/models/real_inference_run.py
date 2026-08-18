from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RealInferenceRun(AIpinhoModel):
    run_id: str
    profile_id: str
    provider_id: str
    model_id: str
    status: str
    real_inference: bool = False
    process_started: bool = False
    output_preview: str = ""
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    audit_event_id: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
