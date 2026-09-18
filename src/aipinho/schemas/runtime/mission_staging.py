from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.mission_contract import MissionResourceScope


class MissionStagingDerivationDecision(AIpinhoModel):
    status: Literal["allowed", "denied"]
    reason_code: str
    resource: MissionResourceScope | None = None
    safe_root: str | None = None
    source_remote_resource_id: str | None = None
    authority_inherited: list[str] = Field(default_factory=list)
    authority_not_inherited: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
