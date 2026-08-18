from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.diagnosis_pipeline_artifact import CandidateTransformationArtifact


PatchCandidateSymbolKind = Literal["file", "function", "class", "method", "property", "block"]


class PatchCandidateArtifact(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"patch_candidate_{uuid4().hex}")
    diagnosis_id: str = ""
    workspace: str
    task_run_id: str | None = None
    execution_plan_id: str | None = None
    semantic_goal: str = ""
    target_file: str
    target_symbol: str
    symbol_kind: PatchCandidateSymbolKind = "file"
    observed_behavior: str
    expected_behavior: str
    evidence_refs: list[str] = Field(default_factory=list)
    risk_level: str = "medium"
    confidence: float = 0.0
    optional_constraints: list[str] = Field(default_factory=list)
    replacement_strategy: str | None = None
    current_content_excerpt: str | None = None
    candidate_transformation: CandidateTransformationArtifact | None = None
    technical_context: dict[str, object] = Field(default_factory=dict)
