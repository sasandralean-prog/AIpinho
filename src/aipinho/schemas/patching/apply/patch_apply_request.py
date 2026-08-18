from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyRequest(AIpinhoModel):
    approval_id: str | None = None
    operator_confirmed: bool = False
    reason: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)
