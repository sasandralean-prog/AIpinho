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


class MissionStagingMaterializationResult(AIpinhoModel):
    status: Literal["materialized", "synchronized", "blocked", "degraded"]
    reason_code: str
    child_task_run_id: str | None = None
    resource_id: str | None = None
    workspace_path: str | None = None
    source_remote_resource_id: str | None = None
    repository_identity: str | None = None
    branch: str | None = None
    directory_execution_id: str | None = None
    clone_execution_id: str | None = None
    fetch_execution_id: str | None = None
    fast_forward_execution_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
