from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


DispatchStatus = Literal["ready", "blocked"]


class DispatchTrace(AIpinhoModel):
    stage: str
    status: str
    reason: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class DispatchRoute(AIpinhoModel):
    route_id: str = Field(default_factory=lambda: f"dispatch_route_{uuid4().hex}")
    operation_type: str
    contract_type: str
    roles: list[str] = Field(default_factory=list)
    approvals_required: list[str] = Field(default_factory=list)
    artifacts_expected: list[str] = Field(default_factory=list)
    validations_required: list[str] = Field(default_factory=list)


class DispatchDecision(AIpinhoModel):
    dispatch_id: str = Field(default_factory=lambda: f"dispatch_{uuid4().hex}")
    status: DispatchStatus = "ready"
    route: DispatchRoute | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[DispatchTrace] = Field(default_factory=list)
