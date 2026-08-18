from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWriteRequest(AIpinhoModel):
    preview_id: str
    approval_id: str
    requested_by: Actor = Field(default_factory=lambda: Actor(type="user", id="local_operator"))
    allow_overwrite: bool = False
    operator_confirmed: bool = False
    include_trace: bool = False
