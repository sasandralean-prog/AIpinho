from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class TransferStatus(AIpinhoModel):
    job_id: str
    transfer_type: str
    status: str = "queued"
    artifact_id: str | None = None
    filename: str | None = None
    progress_percent: float = 0.0
    human_message: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
