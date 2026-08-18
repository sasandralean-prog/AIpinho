from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class TransferIntegrityResult(AIpinhoModel):
    job_id: str
    status: str
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    verified: bool = False
    human_message: str | None = None
