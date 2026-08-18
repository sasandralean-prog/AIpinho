from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class RawViewerRequest(AIpinhoModel):
    raw_ref_id: str
    search: str | None = None
    max_chars: int | None = None
