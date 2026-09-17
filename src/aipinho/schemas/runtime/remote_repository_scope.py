from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RemoteRepositoryIdentity(AIpinhoModel):
    provider: str
    host: str
    repository_path: str
    normalized_identity: str
    normalized_locator: str
    scheme: str
    secret_material_detected: bool = False


class RemoteRepositoryScopeDecision(AIpinhoModel):
    status: Literal["allowed", "denied", "needs_clarification"]
    reason_code: str
    repository_identity: str | None = None
    resource_id: str | None = None
    branch: str | None = None
    operation: str | None = None
    provider: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
