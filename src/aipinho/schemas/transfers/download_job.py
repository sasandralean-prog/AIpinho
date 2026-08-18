from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class DownloadJob(AIpinhoModel):
    job_id: str
    artifact_id: str
    filename: str | None = None
    expected_sha256: str | None = None
    status: str = "queued"
    save_hint: str | None = None
