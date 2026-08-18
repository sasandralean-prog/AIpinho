from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

TargetKind = Literal["none", "self", "workspace", "file", "folder", "url", "memory", "rag_source"]


class TargetReference(AIpinhoModel):
    kind: TargetKind = "none"
    value: str | None = None
    confidence: float = 0.0


class WorkspaceResolution(AIpinhoModel):
    path: str | None = None
    declared: bool = False
    protected: bool = False
    requires_clarification: bool = False
    reason: str | None = None