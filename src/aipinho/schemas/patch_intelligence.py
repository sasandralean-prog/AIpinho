from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, field_validator, model_validator

from aipinho.schemas.common.base import AIpinhoModel


PatchCategory = Literal[
    "intent_regression",
    "lifecycle_regression",
    "workspace_binding_regression",
    "artifact_contract_regression",
    "validation_regression",
    "speaker_truth_regression",
    "approval_regression",
    "dispatcher_regression",
    "timeline_regression",
    "execution_plan_regression",
    "contract_regression",
]
PatchRisk = Literal["low", "medium", "high", "critical"]
PatchConfidence = Literal["low", "medium", "high"]
RelationshipType = Literal["similar_to", "caused_by", "mitigates", "supersedes", "requires"]


ABSOLUTE_PATH_MARKERS = (":\\", ":/", "/home/", "/users/", "/var/", "/tmp/", "/opt/")


def _contains_project_specific_path(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in ABSOLUTE_PATH_MARKERS)
    if isinstance(value, dict):
        return any(_contains_project_specific_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_project_specific_path(item) for item in value)
    return False


class PatchPattern(AIpinhoModel):
    pattern_id: str = Field(default_factory=lambda: f"patch_pattern_{uuid4().hex}")
    category: PatchCategory
    name: str
    description: str
    signals: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)


class PatchEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"patch_evidence_{uuid4().hex}")
    evidence_type: str
    summary: str
    refs: list[str] = Field(default_factory=list)


class PatchRelationship(AIpinhoModel):
    relationship_id: str = Field(default_factory=lambda: f"patch_relationship_{uuid4().hex}")
    relationship_type: RelationshipType
    target_entry_id: str
    rationale: str


class PatchHistory(AIpinhoModel):
    observed_count: int = 0
    successful_strategy_count: int = 0
    failed_strategy_count: int = 0
    last_seen_at: str | None = None
    runtime_versions: list[str] = Field(default_factory=list)


class PatchKnowledgeEntry(AIpinhoModel):
    entry_id: str = Field(default_factory=lambda: f"patch_knowledge_{uuid4().hex}")
    category: PatchCategory
    regression: str
    root_cause: str
    correction_strategy: str
    affected_modules: list[str] = Field(default_factory=list)
    affected_files: list[str] = Field(default_factory=list)
    related_tests: list[str] = Field(default_factory=list)
    related_firetests: list[str] = Field(default_factory=list)
    evidence: list[PatchEvidence] = Field(default_factory=list)
    confidence: PatchConfidence = "medium"
    risk: PatchRisk = "medium"
    runtime_version: str = "unknown"
    patterns: list[PatchPattern] = Field(default_factory=list)
    relationships: list[PatchRelationship] = Field(default_factory=list)
    history: PatchHistory = Field(default_factory=PatchHistory)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_project_specific_paths(self) -> "PatchKnowledgeEntry":
        payload = self.model_dump(mode="json")
        if _contains_project_specific_path(payload):
            raise ValueError("patch_knowledge_entry_must_not_contain_absolute_or_project_specific_paths")
        return self


class PatchKnowledgeBase(AIpinhoModel):
    version: str = "1.0"
    entries: list[PatchKnowledgeEntry] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PatchKnowledgeQuery(AIpinhoModel):
    category: PatchCategory | None = None
    regression: str | None = None
    module: str | None = None
    test: str | None = None
    min_confidence: PatchConfidence | None = None
    limit: int = 20

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if value < 1:
            return 1
        if value > 100:
            return 100
        return value


class PatchKnowledgeQueryResult(AIpinhoModel):
    version: str
    count: int
    entries: list[PatchKnowledgeEntry] = Field(default_factory=list)
    deterministic: bool = True
    stores_patch_code: bool = False


class PatchPatternMatch(AIpinhoModel):
    match_id: str = Field(default_factory=lambda: f"patch_pattern_match_{uuid4().hex}")
    pattern_id: str
    knowledge_entry_id: str
    category: PatchCategory
    confidence: float
    regressions_related: list[str] = Field(default_factory=list)
    suspected_modules: list[str] = Field(default_factory=list)
    recommended_strategy: str
    justification: str
    risks: list[str] = Field(default_factory=list)
    deterministic: bool = True
    prompt_used: bool = False


class PatchPatternRecognitionRequest(AIpinhoModel):
    doctor_report: dict[str, Any] = Field(default_factory=dict)
    regression_matrix: dict[str, Any] = Field(default_factory=dict)
    limit: int = 20

    @field_validator("limit")
    @classmethod
    def validate_pattern_limit(cls, value: int) -> int:
        if value < 1:
            return 1
        if value > 100:
            return 100
        return value


class PatchPatternRecognitionResult(AIpinhoModel):
    count: int
    matches: list[PatchPatternMatch] = Field(default_factory=list)
    deterministic: bool = True
    prompt_used: bool = False
    text_full_match_used: bool = False


class IntelligentPatchProposal(AIpinhoModel):
    proposal_id: str = Field(default_factory=lambda: f"intelligent_patch_proposal_{uuid4().hex}")
    regressions_covered: list[str] = Field(default_factory=list)
    patterns_used: list[str] = Field(default_factory=list)
    modules_candidates: list[str] = Field(default_factory=list)
    files_candidates: list[str] = Field(default_factory=list)
    justification: str
    suggested_strategy: str
    risks: list[str] = Field(default_factory=list)
    rollback_recommended: list[str] = Field(default_factory=list)
    tests_required: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    knowledge_entry_ids: list[str] = Field(default_factory=list)
    patch_plan_refs: list[str] = Field(default_factory=list)
    executor_independent: bool = True
    generates_code: bool = False
    generates_apply_patch: bool = False
    modifies_runtime: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="after")
    def reject_project_specific_paths_in_proposal(self) -> "IntelligentPatchProposal":
        payload = self.model_dump(mode="json")
        if _contains_project_specific_path(payload):
            raise ValueError("intelligent_patch_proposal_must_not_contain_absolute_or_project_specific_paths")
        return self


class IntelligentPatchProposalRequest(AIpinhoModel):
    doctor_report: dict[str, Any] = Field(default_factory=dict)
    regression_matrix: dict[str, Any] = Field(default_factory=dict)
    pattern_matches: list[PatchPatternMatch] = Field(default_factory=list)
    patch_plan: dict[str, Any] = Field(default_factory=dict)


class IntelligentPatchProposalResult(AIpinhoModel):
    proposal: IntelligentPatchProposal
    valid: bool
    validation_errors: list[str] = Field(default_factory=list)
    deterministic: bool = True
    read_only: bool = True
    side_effects: bool = False
