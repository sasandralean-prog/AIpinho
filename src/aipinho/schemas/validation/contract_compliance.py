from __future__ import annotations
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class ContractCompliance(AIpinhoModel):
    status: str
    contract_type: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    executed_actions: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
