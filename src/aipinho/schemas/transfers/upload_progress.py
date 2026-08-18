from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UploadProgress(AIpinhoModel):
    job_id: str
    filename: str
    bytes_sent: int = 0
    total_bytes: int = 0
    percent: float = 0.0
    status: str = "queued"
