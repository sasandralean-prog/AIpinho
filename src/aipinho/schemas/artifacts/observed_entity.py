from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ObservedEntityAttributeStatus = Literal["observed", "inferred", "missing", "unknown"]
ObservedEntityStatus = Literal["observed", "partial", "missing", "inferred"]
WorkspaceRootRole = Literal[
    "project_root",
    "source_code_root",
    "library_root",
    "corpus_root",
    "artifact_root",
    "external_root",
    "build_output_root",
    "cache_root",
    "generated_root",
    "unknown_root",
]


class ObservedEntityAttribute(AIpinhoModel):
    name: str
    value: Any | None = None
    status: ObservedEntityAttributeStatus = "observed"
    confidence: float = 1.0
    evidence_refs: list[str] = Field(default_factory=list)


class ObservedEntity(AIpinhoModel):
    entity_id: str = Field(default_factory=lambda: f"observed_entity_{uuid4().hex}")
    entity_kind: str
    source: str
    source_root: str | None = None
    source_root_role: str | None = None
    relative_path: str | None = None
    entity_role: str | None = None
    entity_domain_hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    selection_eligibility: dict[str, Any] = Field(default_factory=dict)
    exclusion_reasons: list[str] = Field(default_factory=list)
    relationship_eligibility: dict[str, Any] = Field(default_factory=dict)
    relationship_exclusion_reasons: list[str] = Field(default_factory=list)
    relationship_candidate_roles: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    observed_attributes: dict[str, ObservedEntityAttribute] = Field(default_factory=dict)
    inferred_attributes: dict[str, ObservedEntityAttribute] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    observation_status: ObservedEntityStatus = "observed"
    schema_version: str = "observed_entity.v1"


class WorkspaceRootDescriptor(AIpinhoModel):
    root_id: str = Field(default_factory=lambda: f"workspace_root_{uuid4().hex}")
    path: str
    role: WorkspaceRootRole = "unknown_root"
    source: str = "workspace_context"
    aliases: list[str] = Field(default_factory=list)
    purposes: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    policy_status: str = "unknown"
    access_scope: list[str] = Field(default_factory=list)
    observation_allowed: bool = False
    mutation_allowed: bool = False
    policy_reason_codes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class RootBindingEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"root_binding_evidence_{uuid4().hex}")
    root_id: str
    evidence_type: str
    value: Any
    source: str
    confidence: float = 1.0


class RootBindingPolicyDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"root_binding_policy_{uuid4().hex}")
    root_id: str
    policy_status: str
    observation_allowed: bool = False
    mutation_allowed: bool = False
    access_scope: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class RootBinding(AIpinhoModel):
    binding_id: str = Field(default_factory=lambda: f"root_binding_{uuid4().hex}")
    root_id: str
    path: str
    role: WorkspaceRootRole = "unknown_root"
    source: str = "workspace_context"
    purposes: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    policy_decision: RootBindingPolicyDecision
    observation_allowed: bool = False
    mutation_allowed: bool = False
    schema_version: str = "root_binding.v1"


ExternalRootBinding = RootBinding
CorpusRootBinding = RootBinding


class CorpusDescriptor(AIpinhoModel):
    corpus_id: str = Field(default_factory=lambda: f"corpus_{uuid4().hex}")
    root_id: str | None = None
    path: str
    role: str = "corpus_root"
    source: str = "workspace_context"
    confidence: float = 1.0


class EntityEvidenceGraph(AIpinhoModel):
    entity_set_id: str = Field(default_factory=lambda: f"entity_evidence_graph_{uuid4().hex}")
    source: str
    root_descriptors: list[WorkspaceRootDescriptor] = Field(default_factory=list)
    root_bindings: list[RootBinding] = Field(default_factory=list)
    corpus_descriptors: list[CorpusDescriptor] = Field(default_factory=list)
    roots_scanned_by_role: dict[str, list[str]] = Field(default_factory=dict)
    entities_by_root_role: dict[str, int] = Field(default_factory=dict)
    entities: list[ObservedEntity] = Field(default_factory=list)
    semantic_gaps: list[dict[str, Any]] = Field(default_factory=list)
    schema_version: str = "entity_evidence_graph.v1"

    @property
    def entity_count(self) -> int:
        return len(self.entities)


ObservedEntitySet = EntityEvidenceGraph
