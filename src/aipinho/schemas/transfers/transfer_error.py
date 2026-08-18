from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class TransferError(AIpinhoModel):
    job_id: str | None = None
    code: str
    human_message: str
    retryable: bool = False
