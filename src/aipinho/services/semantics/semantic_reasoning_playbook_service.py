from __future__ import annotations

from typing import Any

from aipinho.schemas.semantics.task_semantic_vocabulary import TaskSemanticVocabulary
from aipinho.services.semantics.task_semantic_vocabulary_authority_service import (
    TaskSemanticVocabularyAuthorityService,
)


class SemanticReasoningPlaybookService:
    """Builds governed semantic reasoning context for contract-bound models."""

    _CONSTRAINT_FAMILIES = (
        "do_not_",
        "require_",
        "preserve_",
        "disclose_",
        "prohibit_",
        "restrict_",
        "scope_",
        "avoid_",
        "must_",
    )

    def __init__(
        self,
        *,
        vocabulary_authority: TaskSemanticVocabularyAuthorityService | None = None,
    ) -> None:
        self.vocabulary_authority = (
            vocabulary_authority or TaskSemanticVocabularyAuthorityService()
        )

    def build(
        self,
        *,
        source_payload: dict[str, Any],
        vocabulary: TaskSemanticVocabulary,
    ) -> dict[str, Any]:
        governed_vocabulary = self.vocabulary_authority.governed_view(vocabulary)
        return {
            "playbook_version": "semantic_reasoning_playbook.v1",
            "authority_notice": (
                "Examples are illustrative only. Do not copy identifiers or values. "
                "Derive every output from governed_vocabulary and current_task_semantics."
            ),
            "reasoning_principles": [
                "Determine what the downstream operation intends to do.",
                "Separate execution, evidence, truth, use-safety, and side-effect requirements.",
                "For each upstream semantic dimension, ask whether downstream actually depends on it being true.",
                "Knowledge output does not imply full truth across every upstream domain.",
                "A limitation matters only when it intersects a downstream requirement.",
                "Unknown is not false; inferred is not observed; partial is not absent.",
                "Never invent capabilities, use-safety dimensions, semantic properties, downstream-use identifiers, or evidence.",
                "If no governed identifier represents a concept, leave that requirement empty or unresolved.",
                "Prefer the minimum semantic requirement sufficient for the requested operation.",
                "Produce semantic candidates only; never authorize execution or state transitions.",
            ],
            "governed_vocabulary": governed_vocabulary,
            "vocabulary_binding": vocabulary.binding().model_dump(mode="json"),
            "output_construction_rules": [
                "Governed vocabulary is a selectable lexicon, not an output template.",
                "Include only identifiers that are actually required by the current downstream task.",
                "Do not enumerate every available vocabulary item.",
                "If no downstream-use identifier is required, return required_downstream_uses as an empty list.",
                "If no use-safety dimension is required, return required_use_safety as an empty object.",
                "If a use-safety dimension is included, its acceptable-state list must be non-empty and every state must come from use_safety_requirement_states for that exact dimension.",
                "If no semantic property is required, return required_semantic_properties as an empty object.",
                "Never use vocabulary container names such as semantic_property_identifiers as output property identifiers.",
                "Confidence measures confidence in the semantic interpretation, not how many requirements were selected.",
                "An empty requirement set may have high confidence when the current task clearly does not depend on upstream semantic guarantees.",
            ],
            "confidence_calibration": {
                "high": (
                    "0.80-1.00 when current task semantics are explicit enough to "
                    "determine the required guarantees, including a confident conclusion "
                    "that no upstream semantic guarantee is required."
                ),
                "medium": (
                    "0.65-0.79 when requirements can be derived but some non-critical "
                    "semantic ambiguity remains."
                ),
                "low": (
                    "0.00-0.64 only when the task semantics are insufficient or ambiguous "
                    "enough that the requirement set itself is uncertain."
                ),
                "warning": (
                    "Do not lower confidence merely because requirement lists or mappings "
                    "are empty. Empty and uncertain are different states."
                ),
            },
            "empty_requirement_output_example": {
                "instruction": (
                    "Structure-only example. Use when the current task clearly "
                    "requires no upstream semantic guarantee. Do not copy confidence."
                ),
                "required_downstream_uses": [],
                "required_use_safety": {},
                "required_semantic_properties": {},
                "base_constraints": [],
                "risk_constraints": [],
            },
            "generic_examples": self._examples(),
            "generic_counterexamples": self._counterexamples(),
            "current_task_semantics": source_payload,
        }

    def _examples(self) -> list[dict[str, Any]]:
        return [
            {
                "label": "illustrative_A_do_not_copy",
                "upstream": {
                    "property_X": "inferred",
                    "safe_for_operation_Y": "true_with_limitations",
                },
                "downstream": {
                    "depends_on": ["property_Z"],
                    "does_not_claim": ["property_X"],
                    "side_effects": "none",
                },
                "correct_reasoning": (
                    "The limitation on property_X does not automatically block. "
                    "Evaluate whether it intersects property_Z or operation_Y."
                ),
            },
            {
                "label": "illustrative_B_do_not_copy",
                "upstream": {
                    "safe_for_truth_claim": False,
                    "safe_for_catalog": True,
                },
                "downstream": {
                    "purpose": "reorganize a representation",
                    "authoritative_identity_claim": False,
                },
                "correct_reasoning": (
                    "Truth-claim safety may be irrelevant while catalog safety may be relevant."
                ),
            },
            {
                "label": "illustrative_C_do_not_copy",
                "upstream": {
                    "safe_for_catalog": True,
                    "safe_for_destructive_action": False,
                },
                "downstream": {"side_effect": "destructive"},
                "correct_reasoning": (
                    "Block when destructive safety is required and unavailable."
                ),
            },
            {
                "label": "illustrative_D_do_not_copy",
                "upstream": {"relation_A": "unresolved"},
                "downstream": {"dependency_on_relation_A": "unknown"},
                "correct_reasoning": (
                    "Return unknown or insufficient evidence rather than assuming compatibility."
                ),
            },
        ]

    def _counterexamples(self) -> list[dict[str, str]]:
        return [
            {
                "wrong": "knowledge_output=true therefore safe_for_truth_claim=true",
                "why_wrong": (
                    "Knowledge may concern only a subset of upstream semantic domains."
                ),
                "better": (
                    "Identify which claim domains the downstream output actually depends on."
                ),
            },
            {
                "wrong": "upstream has limitations therefore block",
                "why_wrong": (
                    "A limitation may concern a semantic dimension irrelevant to downstream."
                ),
                "better": (
                    "Evaluate each limitation against frozen downstream demand."
                ),
            },
            {
                "wrong": "upstream is partially satisfied therefore admit",
                "why_wrong": (
                    "A limitation may intersect a critical downstream requirement."
                ),
                "better": (
                    "Use partial outcome only as eligible evidence for compatibility evaluation."
                ),
            },
            {
                "wrong": "turn a deliverable label into a downstream-use identifier",
                "why_wrong": (
                    "Deliverables describe outputs; governed use identifiers describe permitted semantic use."
                ),
                "better": (
                    "Select only identifiers listed in governed_vocabulary."
                ),
            },
        ]
