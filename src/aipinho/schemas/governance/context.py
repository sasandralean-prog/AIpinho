from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class WorkspaceAnalysisRequirement(AIpinhoModel):
    requires_workspace: bool = False
    requires_discovery: bool = False
    requires_analysis_ref: bool = False
    reason: str = ""


class DiscoverySnapshotRef(AIpinhoModel):
    ref_id: str
    workspace_path: str | None = None
    source: str = "canonical_context_gate"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisRef(AIpinhoModel):
    ref_id: str
    discovery_ref: str | None = None
    source: str = "canonical_context_gate"
    metadata: dict[str, Any] = Field(default_factory=dict)
