from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class DecisionOwner(AIpinhoModel):
    decision: str
    owner: str
    rationale: str
    ui_can_override: bool = False


class DecisionOwnershipMatrix(AIpinhoModel):
    status: str
    owners: list[DecisionOwner] = Field(default_factory=list)
