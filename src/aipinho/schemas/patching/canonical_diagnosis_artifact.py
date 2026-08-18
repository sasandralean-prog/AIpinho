from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.diagnosis_pipeline_artifact import (
    BehaviorJustificationArtifact,
    BehaviorLocalizationArtifact,
    SemanticEvidenceArtifact,
)


DiagnosisSymbolKind = Literal["file", "function", "class", "method", "property", "block"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DiagnosisMetadata(AIpinhoModel):
    source_type: str = "runtime_analysis"
    source_id: str | None = None
    task_id: str | None = None
    task_run_id: str | None = None
    execution_plan_id: str | None = None
    created_at: str = Field(default_factory=_utc_now)


class TechnicalLocalization(AIpinhoModel):
    workspace: str
    target_file: str
    target_symbol: str
    symbol_kind: DiagnosisSymbolKind = "file"
    region_hint: str | None = None
    confidence: float = 0.0


class DiagnosisEvidenceRef(AIpinhoModel):
    evidence_id: str
    source_type: str = "artifact"
    source_path: str | None = None
    summary: str = ""
    confidence: float = 0.0


class RepairHint(AIpinhoModel):
    strategy: str
    related_symbols: list[str] = Field(default_factory=list)
    affected_dependencies: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class RepairIntent(AIpinhoModel):
    intent_id: str = Field(default_factory=lambda: f"repair_intent_{uuid4().hex}")
    target_file: str
    target_symbol: str
    expected_behavior: str
    repair_boundary: list[str] = Field(default_factory=list)
    success_condition: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)


class CanonicalDiagnosisArtifact(AIpinhoModel):
    diagnosis_id: str = Field(default_factory=lambda: f"diagnosis_{uuid4().hex}")
    metadata: DiagnosisMetadata = Field(default_factory=DiagnosisMetadata)
    diagnosis_type: str = "technical_diagnosis"
    workspace: str
    semantic_goal: str = ""
    observed_behavior: str
    expected_behavior: str
    technical_localization: list[TechnicalLocalization] = Field(default_factory=list)
    evidence: list[DiagnosisEvidenceRef] = Field(default_factory=list)
    confidence: float = 0.0
    repair_hints: list[RepairHint] = Field(default_factory=list)
    repair_intent: RepairIntent | None = None
    semantic_evidence: SemanticEvidenceArtifact | None = None
    behavior_localization: BehaviorLocalizationArtifact | None = None
    behavior_justification: BehaviorJustificationArtifact | None = None
    reason_codes: list[str] = Field(default_factory=list)
