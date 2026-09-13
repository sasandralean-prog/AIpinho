from __future__ import annotations

from aipinho.schemas.semantics.task_semantic_vocabulary import (
    SemanticConceptDefinition,
    SemanticConceptProvenance,
)
from aipinho.services.artifacts.artifact_use_safety_service import (
    ArtifactUseSafetyService,
)


class SystemSemanticVocabularyService:
    """System-owned semantic types and identifiers shared by all tasks."""

    VERSION = "system_semantic_vocabulary.v1"

    _EPISTEMIC_STATES = (
        "observed",
        "inferred",
        "derived",
        "unknown",
        "not_applicable",
    )
    _EPISTEMIC_REQUIREMENT_STATES = (
        "observed",
        "inferred",
        "derived",
    )
    _WORK_MODES = (
        "observation",
        "discovery",
        "analysis",
        "comparison",
        "hypothesis_generation",
        "experimentation",
        "planning",
        "mutation",
        "execution",
        "validation",
        "reporting",
    )
    _CONSTRAINT_FAMILIES = (
        "do_not",
        "require",
        "preserve",
        "disclose",
        "prohibit",
        "restrict",
        "scope",
        "avoid",
        "must",
    )
    _EFFECTS = (
        "knowledge_only",
        "planning_only",
        "proposal_only",
        "workspace_mutation",
        "build_execution",
        "runtime_execution",
        "approval_command",
        "immutable",
        "mutable",
        "prohibited",
        "command_execution",
        "destructive_action",
    )
    def concept_type_state_domains(self) -> dict[str, list[bool | int | float | str]]:
        epistemic = list(self._EPISTEMIC_STATES)
        return {
            "use_safety": [],
            "epistemic_property": epistemic,
            "behavioral_property": epistemic,
            "structural_property": epistemic,
            "relationship": epistemic,
            "downstream_use": [],
            "capability": [],
            "constraint_family": [],
            "work_mode": [],
            "evidence_domain": [],
            "effect": [],
        }

    def concept_type_requirement_domains(
        self,
    ) -> dict[str, list[bool | int | float | str]]:
        epistemic = list(self._EPISTEMIC_REQUIREMENT_STATES)
        return {
            "use_safety": [],
            "epistemic_property": epistemic,
            "behavioral_property": epistemic,
            "structural_property": epistemic,
            "relationship": epistemic,
            "downstream_use": [],
            "capability": [],
            "constraint_family": [],
            "work_mode": [],
            "evidence_domain": [],
            "effect": [],
        }

    def concepts(self) -> list[SemanticConceptDefinition]:
        concepts: list[SemanticConceptDefinition] = []
        provenance = [
            SemanticConceptProvenance(
                source_kind="system_authority",
                source_ref=self.VERSION,
            )
        ]
        observed_states = ArtifactUseSafetyService.governed_dimension_states()
        requirement_states = ArtifactUseSafetyService.governed_requirement_states()
        for concept_id in ArtifactUseSafetyService.governed_dimensions():
            concepts.append(
                SemanticConceptDefinition(
                    concept_id=concept_id,
                    concept_type="use_safety",
                    scope="system",
                    allowed_states=list(observed_states.get(concept_id) or []),
                    requirement_states=list(
                        requirement_states.get(concept_id) or []
                    ),
                    provenance=provenance,
                )
            )
        for concept_id in self._WORK_MODES:
            concepts.append(
                SemanticConceptDefinition(
                    concept_id=concept_id,
                    concept_type="work_mode",
                    scope="system",
                    provenance=provenance,
                )
            )
        for concept_id in self._CONSTRAINT_FAMILIES:
            concepts.append(
                SemanticConceptDefinition(
                    concept_id=concept_id,
                    concept_type="constraint_family",
                    scope="system",
                    provenance=provenance,
                )
            )
        for concept_id in self._EFFECTS:
            concepts.append(
                SemanticConceptDefinition(
                    concept_id=concept_id,
                    concept_type="effect",
                    scope="system",
                    provenance=provenance,
                )
            )
        return concepts

    def constraint_families(self) -> tuple[str, ...]:
        return self._CONSTRAINT_FAMILIES

    def work_modes(self) -> tuple[str, ...]:
        return self._WORK_MODES
