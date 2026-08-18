from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class QualityAnalysis(AIpinhoModel):
    score: int = 0
    confidence: str = "baixa"
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class RepairTaskArtifact(AIpinhoModel):
    repair_task_id: str = ""
    diagnosis_id: str = ""
    candidate_id: str = ""
    workspace: str = ""
    target_file: str = ""
    target_symbol: str = ""
    symbol_kind: str = "file"
    edit_unit: str = "unknown"
    semantic_goal: str = ""
    why_change: str = ""
    behavior_to_create: str = ""
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    success_condition: str = ""
    repair_boundary: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    current_content_chars: int = 0
    source_content_chars: int = 0
    current_content_complete: bool = False
    actionability_score: int = 0
    actionable: bool = False
    missing: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class ActionabilityAnalysis(AIpinhoModel):
    score: int = 0
    confidence: str = "baixa"
    editable: bool = False
    edit_unit: str = "unknown"
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    repair_task: RepairTaskArtifact = Field(default_factory=RepairTaskArtifact)


class AlignmentAnalysis(AIpinhoModel):
    score: int = 0
    confidence: str = "baixa"
    aligned: bool = False
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
