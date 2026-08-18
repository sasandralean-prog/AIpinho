from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


DiagnosisPipelineStatus = Literal["complete", "partial", "missing", "invalid"]


class SemanticEvidenceEntry(AIpinhoModel):
    evidence_id: str = ""
    source_type: str = "artifact"
    source_path: str | None = None
    target_file: str = ""
    target_symbol: str = ""
    excerpt: str = ""
    relation: str = ""
    confidence: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)


class SemanticEvidenceArtifact(AIpinhoModel):
    artifact_id: str = Field(default_factory=lambda: f"semantic_evidence_{uuid4().hex}")
    diagnosis_id: str = ""
    status: DiagnosisPipelineStatus = "missing"
    coverage_score: int = 0
    confidence: float = 0.0
    evidence: list[SemanticEvidenceEntry] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class BehaviorLocalizationArtifact(AIpinhoModel):
    artifact_id: str = Field(default_factory=lambda: f"behavior_localization_{uuid4().hex}")
    diagnosis_id: str = ""
    status: DiagnosisPipelineStatus = "missing"
    target_file: str = ""
    target_symbol: str = ""
    symbol_kind: str = "file"
    anchor_kind: str = "file"
    anchor_name: str = ""
    anchor_signature: str = ""
    localized_behavior: str = ""
    localized_excerpt: str = ""
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    coverage_score: int = 0
    confidence: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class BehaviorJustificationArtifact(AIpinhoModel):
    artifact_id: str = Field(default_factory=lambda: f"behavior_justification_{uuid4().hex}")
    diagnosis_id: str = ""
    status: DiagnosisPipelineStatus = "missing"
    observed_behavior: str = ""
    expected_behavior: str = ""
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    reasoning_chain: list[str] = Field(default_factory=list)
    coverage_score: int = 0
    confidence: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class CandidateTransformationArtifact(AIpinhoModel):
    artifact_id: str = Field(default_factory=lambda: f"candidate_transformation_{uuid4().hex}")
    diagnosis_id: str = ""
    candidate_id: str = ""
    status: DiagnosisPipelineStatus = "missing"
    target_file: str = ""
    target_symbol: str = ""
    current_logic: str = ""
    desired_logic: str = ""
    transformation_strategy: str = ""
    constraints: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    affected_symbols: list[str] = Field(default_factory=list)
    behavior_summary: str = ""
    coverage_score: int = 0
    confidence: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
