from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


MissionExecutionMode = Literal[
    "single_operation",
    "staged",
    "end_to_end_governed",
]
MissionResourceType = Literal[
    "local_workspace",
    "remote_repository",
    "external_resource",
]


class MissionConstraint(AIpinhoModel):
    constraint_id: str
    kind: str
    effect: Literal["require", "deny", "limit"] = "limit"
    subject: str | None = None
    value: Any = None
    source_ref: str | None = None


class MissionResourceScope(AIpinhoModel):
    resource_id: str
    resource_type: MissionResourceType
    role: str | None = None
    locator: str | None = None
    provider: str | None = None
    normalized_identity: str | None = None
    allowed_branches: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    constraints: list[MissionConstraint] = Field(default_factory=list)
    derived_from: str | None = None
    provenance_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MissionAuthorityBinding(AIpinhoModel):
    requested_capabilities: list[str] = Field(default_factory=list)
    authorized_capabilities: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class MissionCompletionContract(AIpinhoModel):
    validation_requirements: list[str] = Field(default_factory=list)
    completion_requirements: list[str] = Field(default_factory=list)
    allow_limited_completion: bool = False


class MissionContractBinding(AIpinhoModel):
    mission_id: str
    authority_sha256: str
    revision: int
    source_prompt_sha256: str
    strategy: MissionExecutionMode


class MissionContract(AIpinhoModel):
    mission_id: str
    session_id: str | None = None
    source_message_id: str
    source_prompt_sha256: str
    objective: str
    strategy: MissionExecutionMode = "single_operation"
    local_resources: list[MissionResourceScope] = Field(default_factory=list)
    remote_resources: list[MissionResourceScope] = Field(default_factory=list)
    authority: MissionAuthorityBinding = Field(default_factory=MissionAuthorityBinding)
    negative_constraints: list[MissionConstraint] = Field(default_factory=list)
    completion: MissionCompletionContract = Field(default_factory=MissionCompletionContract)
    provenance_refs: list[str] = Field(default_factory=list)
    revision: int = 1
    parent_authority_sha256: str | None = None
    authority_sha256: str
    status: Literal["frozen"] = "frozen"
    frozen_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "mission_contract.v1"


    def binding(self) -> MissionContractBinding:
        return MissionContractBinding(
            mission_id=self.mission_id,
            authority_sha256=self.authority_sha256,
            revision=self.revision,
            source_prompt_sha256=self.source_prompt_sha256,
            strategy=self.strategy,
        )
