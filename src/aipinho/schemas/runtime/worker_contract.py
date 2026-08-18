from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


WorkerContractStatus = Literal["active", "disabled", "deprecated"]


class WorkerContract(AIpinhoModel):
    worker_id: str
    display_name: str
    status: WorkerContractStatus = "active"
    responsibilities: list[str] = Field(default_factory=list)
    accepted_actions: list[str] = Field(default_factory=list)
    accepted_step_keywords: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    output_contracts: list[str] = Field(default_factory=list)
    communicates_via_contracts: bool = True
    knows_internal_implementation_of_peers: bool = False


class WorkerRouteDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"worker_route_{uuid4().hex}")
    worker_id: str
    matched_by: Literal["action", "keyword", "default"]
    reason: str
    confidence: Literal["low", "medium", "high"] = "medium"
    action: str | None = None
    step_type: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    output_contracts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class WorkerRegistrySnapshot(AIpinhoModel):
    status: Literal["ok", "degraded"] = "ok"
    workers: list[WorkerContract] = Field(default_factory=list)
    default_worker: str = "PlannerWorker"
    warnings: list[str] = Field(default_factory=list)
