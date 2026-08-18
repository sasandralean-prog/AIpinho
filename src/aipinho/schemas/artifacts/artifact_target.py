from __future__ import annotations

from pydantic import Field

from aipinho.schemas.artifacts.artifact_trace import ArtifactTraceItem
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactTarget(AIpinhoModel):
    workspace: str
    target_path: str
    normalized_target_path: str | None = None
    relative_target_path: str | None = None
    extension: str = ""
    base_dir: str = ""


class ArtifactTargetValidation(AIpinhoModel):
    valid: bool = False
    workspace_allowed: bool = False
    target_allowed: bool = False
    extension_allowed: bool = False
    base_dir_allowed: bool = False
    forbidden_root: bool = False
    path_traversal: bool = False
    outside_workspace: bool = False
    would_overwrite: bool = False
    source_code_target: bool = False
    config_mutation_target: bool = False
    script_target: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[ArtifactTraceItem] = Field(default_factory=list)
    target: ArtifactTarget | None = None
