from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


SemanticConceptType = Literal[
    "use_safety",
    "epistemic_property",
    "behavioral_property",
    "structural_property",
    "relationship",
    "downstream_use",
    "capability",
    "constraint_family",
    "work_mode",
    "evidence_domain",
    "effect",
]
SemanticConceptScope = Literal["system", "task"]
SemanticVocabularySourceKind = Literal[
    "system_authority",
    "canonical_execution_plan",
    "canonical_execution_step",
    "intent_map",
    "semantic_intent_graph",
    "task_plan",
    "deterministic_revision",
    "model_candidate",
    "deterministic_gate",
]
SemanticScalar = bool | int | float | str


class SemanticConceptProvenance(AIpinhoModel):
    source_kind: SemanticVocabularySourceKind
    source_ref: str
    source_field: str | None = None
    source_sha256: str | None = None


class SemanticConceptDefinition(AIpinhoModel):
    concept_id: str
    concept_type: SemanticConceptType
    scope: SemanticConceptScope
    allowed_states: list[SemanticScalar] = Field(default_factory=list)
    requirement_states: list[SemanticScalar] = Field(default_factory=list)
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    provenance: list[SemanticConceptProvenance] = Field(default_factory=list)
class TaskSemanticVocabularyBinding(AIpinhoModel):
    vocabulary_id: str
    authority_sha256: str
    revision: int
    source_semantics_sha256: str


class TaskSemanticVocabulary(AIpinhoModel):
    vocabulary_id: str
    task_run_id: str | None = None
    task_id: str | None = None
    source_plan_id: str | None = None
    source_execution_id: str | None = None
    source_semantics_sha256: str
    revision: int = 1
    parent_vocabulary_id: str | None = None
    parent_authority_sha256: str | None = None
    revision_reason: str | None = None
    revision_source_ref: str | None = None
    concepts: list[SemanticConceptDefinition] = Field(default_factory=list)
    concept_type_state_domains: dict[str, list[SemanticScalar]] = Field(default_factory=dict)
    concept_type_requirement_domains: dict[str, list[SemanticScalar]] = Field(default_factory=dict)
    status: Literal["frozen"] = "frozen"
    authority_sha256: str
    frozen_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "task_semantic_vocabulary.v1"

    def binding(self) -> TaskSemanticVocabularyBinding:
        return TaskSemanticVocabularyBinding(
            vocabulary_id=self.vocabulary_id,
            authority_sha256=self.authority_sha256,
            revision=self.revision,
            source_semantics_sha256=self.source_semantics_sha256,
        )


class TaskSemanticVocabularyCompilation(AIpinhoModel):
    status: Literal["compiled", "insufficient_contract_evidence"]
    vocabulary: TaskSemanticVocabulary | None = None
    reason_codes: list[str] = Field(default_factory=list)
    source_semantics_sha256: str | None = None
class TaskSemanticVocabularyRevisionRequest(AIpinhoModel):
    revision_request_id: str = Field(
        default_factory=lambda: f"semantic_vocabulary_revision_{uuid4().hex}"
    )
    parent_vocabulary_id: str
    parent_authority_sha256: str
    reason: str
    concepts_to_add: list[SemanticConceptDefinition] = Field(default_factory=list)
    source_ref: str | None = None


class TaskSemanticVocabularyRevisionResult(AIpinhoModel):
    status: Literal["revised", "rejected"]
    vocabulary: TaskSemanticVocabulary | None = None
    reason_codes: list[str] = Field(default_factory=list)
