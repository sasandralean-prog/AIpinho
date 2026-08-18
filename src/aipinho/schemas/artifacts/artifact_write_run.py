from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWriteRun(AIpinhoModel):
    write_run_id: str
    preview_id: str
    approval_id: str
    status: str = "created"
    workspace: str
    target_path: str
    relative_target_path: str | None = None
    content_hash: str = ""
    preview_status_snapshot: str = ""
    approval_status_snapshot: str = ""
    approval_scope_snapshot: str = ""
    would_overwrite: bool = False
    allow_overwrite: bool = False
    operator_confirmed: bool = False
    requested_by: Actor = Field(default_factory=Actor)
    backup_id: str | None = None
    result_id: str | None = None
    created_at: str
    updated_at: str
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
