from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UploadJob(AIpinhoModel):
    job_id: str
    filename: str
    size_bytes: int = 0
    content_type: str | None = None
    status: str = "queued"
