from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class DownloadProgress(AIpinhoModel):
    job_id: str
    artifact_id: str
    bytes_received: int = 0
    total_bytes: int = 0
    percent: float = 0.0
    status: str = "queued"
