from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

WorkspaceReferenceRole = Literal[
    "source_readonly",
    "target_mutable",
    "workspace",
    "unknown",
]


class WorkspaceReference(AIpinhoModel):
    path: str
    role: WorkspaceReferenceRole = "unknown"
    evidence: str | None = None
    confidence: float = 0.0
