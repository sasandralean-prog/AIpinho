from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class WorkspaceDiscoverySnapshot(AIpinhoModel):
    snapshot_ref: str
    workspace_path: str
    status: str = "metadata_only"
    files_sampled: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
