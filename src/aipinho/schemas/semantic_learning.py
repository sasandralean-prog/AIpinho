from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, field_validator, model_validator

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation


SemanticConfidence = Literal["low", "medium", "high"]
SemanticRelationshipType = Literal["similar_to", "generalizes", "requires", "contrasts", "supports"]
SemanticMaturity = Literal["UNKNOWN", "EXPERIMENTAL", "LEARNING", "STABLE", "CANONICAL", "DEPRECATED", "REMOVED"]

ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]", re.IGNORECASE),
    re.compile(r"(^|[\s'\"])/(home|users|var|tmp|opt)/", re.IGNORECASE),
)
SECRET_MARKERS = ("sk-", "api_key", "apikey", "token=", "secret=", "password=", "bearer ")
PERSONAL_MARKERS = ("cpf", "ssn", "email:", "phone:", "telefone:", "endereco:", "endereço:")


def _contains_forbidden_semantic_data(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        if any(pattern.search(value) for pattern in ABSOLUTE_PATH_PATTERNS):
            return True
        return any(marker in lowered for marker in (*SECRET_MARKERS, *PERSONAL_MARKERS))
    if isinstance(value, dict):
        return any(_contains_forbidden_semantic_data(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_semantic_data(item) for item in value)
    return False


class SemanticVersion(AIpinhoModel):
    version: str = "1.0"
    schema_name: str = "SemanticKnowledgeBase"
    compatible_from: str = "1.0"


class SemanticConcept(AIpinhoModel):
    concept_id: str = Field(default_factory=lambda: f"semantic_concept_{uuid4().hex}")
    name: str
    canonical_intent: str
    scope: str
    description: str
    tags: list[str] = Field(default_factory=list)


class SemanticPattern(AIpinhoModel):
    pattern_id: str = Field(default_factory=lambda: f"semantic_pattern_{uuid4().hex}")
    concept_id: str
    canonical_intent: str
    scope: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)


class SemanticRelationship(AIpinhoModel):
    relationship_id: str = Field(default_factory=lambda: f"semantic_relationship_{uuid4().hex}")
    relationship_type: SemanticRelationshipType
    target_concept_id: str
    rationale: str


class SemanticEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"semantic_evidence_{uuid4().hex}")
    evidence_type: str
    summary: str
    refs: list[str] = Field(default_factory=list)


class SemanticKnowledgeEntry(AIpinhoModel):
    entry_id: str = Field(default_factory=lambda: f"semantic_knowledge_{uuid4().hex}")
    concept: SemanticConcept
    entities_identified: list[str] = Field(default_factory=list)
    canonical_intent: str
    scope: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    confidence: SemanticConfidence = "medium"
    ambiguities: list[str] = Field(default_factory=list)
    isr: IntermediateSemanticRepresentation
    evidence: list[SemanticEvidence] = Field(default_factory=list)
    version: SemanticVersion = Field(default_factory=SemanticVersion)
    patterns: list[SemanticPattern] = Field(default_factory=list)
    relationships: list[SemanticRelationship] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_semantic_only(self) -> "SemanticKnowledgeEntry":
        payload = self.model_dump(mode="json")
        if _contains_forbidden_semantic_data(payload):
            raise ValueError("semantic_knowledge_must_not_contain_paths_personal_data_tokens_or_secrets")
        if self.isr.reasoning_summary and len(self.isr.reasoning_summary.split()) > 40:
            raise ValueError("semantic_knowledge_must_not_store_full_prompt_or_long_freeform_reasoning")
        return self


class SemanticKnowledgeBase(AIpinhoModel):
    version: SemanticVersion = Field(default_factory=SemanticVersion)
    entries: list[SemanticKnowledgeEntry] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SemanticKnowledgeQuery(AIpinhoModel):
    canonical_intent: str | None = None
    scope: str | None = None
    concept: str | None = None
    entity: str | None = None
    min_confidence: SemanticConfidence | None = None
    limit: int = 20

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if value < 1:
            return 1
        if value > 100:
            return 100
        return value


class SemanticKnowledgeQueryResult(AIpinhoModel):
    version: str
    count: int
    entries: list[SemanticKnowledgeEntry] = Field(default_factory=list)
    deterministic: bool = True
    stores_full_prompt: bool = False
    stores_project_specific_data: bool = False


class SemanticConceptList(AIpinhoModel):
    version: str
    count: int
    concepts: list[SemanticConcept] = Field(default_factory=list)
    deterministic: bool = True


class SemanticPatternMatch(AIpinhoModel):
    match_id: str = Field(default_factory=lambda: f"semantic_pattern_match_{uuid4().hex}")
    pattern_id: str
    concept: SemanticConcept
    frequency: int = 1
    confidence: float = 0.0
    examples: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    relationships: list[SemanticRelationship] = Field(default_factory=list)
    matched_entities: list[str] = Field(default_factory=list)
    matched_constraints: dict[str, Any] = Field(default_factory=dict)
    deterministic: bool = True
    prompt_used: bool = False
    modifies_runtime: bool = False


class SemanticPatternRecognitionRequest(AIpinhoModel):
    isr: IntermediateSemanticRepresentation | dict[str, Any]
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


class SemanticPatternRecognitionResult(AIpinhoModel):
    count: int
    matches: list[SemanticPatternMatch] = Field(default_factory=list)
    deterministic: bool = True
    prompt_used: bool = False
    modifies_runtime: bool = False


class SemanticRecommendation(AIpinhoModel):
    recommendation_id: str = Field(default_factory=lambda: f"semantic_recommendation_{uuid4().hex}")
    related_concept: SemanticConcept
    justification: str
    expected_benefit: str
    risks: list[str] = Field(default_factory=list)
    candidate_modules: list[str] = Field(default_factory=list)
    estimated_impact: Literal["low", "medium", "high"] = "medium"
    confidence: float = 0.0
    evidence: list[SemanticEvidence] = Field(default_factory=list)
    status: Literal["pending_human_validation", "accepted", "rejected"] = "pending_human_validation"
    modifies_semantic_interpreter: bool = False
    modifies_contract_compiler: bool = False
    modifies_governed_runtime: bool = False
    modifies_runtime_contracts: bool = False
    modifies_models: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SemanticRecommendationRequest(AIpinhoModel):
    semantic_patterns: list[SemanticPatternMatch] = Field(default_factory=list)
    doctor_report: dict[str, Any] = Field(default_factory=dict)
    regression_matrix: dict[str, Any] = Field(default_factory=dict)
    patch_knowledge_base: dict[str, Any] = Field(default_factory=dict)
    limit: int = 20

    @field_validator("limit")
    @classmethod
    def validate_recommendation_limit(cls, value: int) -> int:
        if value < 1:
            return 1
        if value > 100:
            return 100
        return value


class SemanticRecommendationResult(AIpinhoModel):
    count: int
    recommendations: list[SemanticRecommendation] = Field(default_factory=list)
    deterministic: bool = True
    read_only: bool = True
    side_effects: bool = False
    pending_human_validation: bool = True


class SemanticCapability(AIpinhoModel):
    capability_id: str = Field(default_factory=lambda: f"semantic_capability_{uuid4().hex}")
    name: str
    description: str
    domain: str
    version: SemanticVersion = Field(default_factory=lambda: SemanticVersion(schema_name="SemanticCapability"))


class SemanticCompetency(AIpinhoModel):
    competency_id: str = Field(default_factory=lambda: f"semantic_competency_{uuid4().hex}")
    name: str
    description: str
    domain: str
    dependencies: list[str] = Field(default_factory=list)
    knowledge_used: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    firetests_related: list[str] = Field(default_factory=list)
    version: SemanticVersion = Field(default_factory=lambda: SemanticVersion(schema_name="SemanticCompetency"))


class SemanticMilestone(AIpinhoModel):
    milestone_id: str = Field(default_factory=lambda: f"semantic_milestone_{uuid4().hex}")
    title: str
    summary: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_refs: list[str] = Field(default_factory=list)


class SemanticEvolution(AIpinhoModel):
    evolution_id: str = Field(default_factory=lambda: f"semantic_evolution_{uuid4().hex}")
    version: str = "1.0"
    changes: list[str] = Field(default_factory=list)
    milestones: list[SemanticMilestone] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SemanticPromotionCandidate(AIpinhoModel):
    promotion_candidate_id: str = Field(default_factory=lambda: f"semantic_promotion_{uuid4().hex}")
    competency: SemanticCompetency
    reason: str
    knowledge_used: list[str] = Field(default_factory=list)
    patterns_used: list[str] = Field(default_factory=list)
    evidence: list[SemanticEvidence] = Field(default_factory=list)
    regressions_related: list[str] = Field(default_factory=list)
    expected_impact: str
    risks: list[str] = Field(default_factory=list)
    rollback: list[str] = Field(default_factory=list)
    approval_required: bool = True
    status: Literal["candidate", "approved_for_future_version", "rejected"] = "candidate"
    auto_promoted: bool = False
    modifies_runtime: bool = False


class SemanticCurriculumEntry(AIpinhoModel):
    curriculum_entry_id: str = Field(default_factory=lambda: f"semantic_curriculum_entry_{uuid4().hex}")
    concept: SemanticConcept
    competency: SemanticCompetency
    learned_patterns: list[str] = Field(default_factory=list)
    evidence: list[SemanticEvidence] = Field(default_factory=list)
    recommendations_accepted: list[str] = Field(default_factory=list)
    recommendations_rejected: list[str] = Field(default_factory=list)
    regressions_associated: list[str] = Field(default_factory=list)
    firetests_related: list[str] = Field(default_factory=list)
    maturity: SemanticMaturity = "LEARNING"
    version: SemanticVersion = Field(default_factory=lambda: SemanticVersion(schema_name="SemanticCurriculumEntry"))


class SemanticCurriculum(AIpinhoModel):
    curriculum_id: str = "semantic_curriculum_default"
    version: SemanticVersion = Field(default_factory=lambda: SemanticVersion(schema_name="SemanticCurriculum"))
    entries: list[SemanticCurriculumEntry] = Field(default_factory=list)
    capabilities: list[SemanticCapability] = Field(default_factory=list)
    evolutions: list[SemanticEvolution] = Field(default_factory=list)
    promotion_candidates: list[SemanticPromotionCandidate] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    auto_changes_runtime: bool = False


class SemanticCurriculumReviewRequest(AIpinhoModel):
    recommendation_id: str
    decision: Literal["accepted", "rejected"]
    reviewer: str = "human_operator"
    rationale: str = ""


class SemanticCurriculumPromoteRequest(AIpinhoModel):
    curriculum_entry_id: str
    reason: str
    expected_impact: str = "Improve future semantic runtime consistency."


class SemanticCurriculumResult(AIpinhoModel):
    curriculum: SemanticCurriculum
    report_markdown: str
    evolution_history: dict[str, Any]
    read_only: bool = True
    side_effects: bool = False
