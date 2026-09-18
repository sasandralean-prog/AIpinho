from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class MissionCompletionSnapshot(AIpinhoModel):
    mission_id: str
    status: Literal["ready", "missing", "invalid"]
    reason_codes: list[str] = Field(default_factory=list)
    source_prompt_sha256: str | None = None
    strategy: str | None = None
    completion_requirements: list[str] = Field(default_factory=list)
    validation_requirements: list[str] = Field(default_factory=list)
    allow_limited_completion: bool = False
    task_run_ids: list[str] = Field(default_factory=list)
    terminal_task_run_ids: list[str] = Field(default_factory=list)
    phase_outcome_run_ids: list[str] = Field(default_factory=list)
    phase_outcome_authority_sha256s: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    contract_authority_sha256s: list[str] = Field(default_factory=list)
    contract_revisions: list[int] = Field(default_factory=list)
    authority_sha256: str
    projected_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "mission_completion_snapshot.v1"
