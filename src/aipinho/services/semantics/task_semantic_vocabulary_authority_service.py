from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.semantics.task_semantic_vocabulary import (
    SemanticConceptDefinition,
    TaskSemanticVocabulary,
)


class TaskSemanticVocabularyAuthorityService:
    """Hashes, verifies and projects frozen task semantic vocabularies."""

    def stable_sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def authority_payload(
        self,
        *,
        task_run_id: str | None,
        task_id: str | None,
        source_plan_id: str | None,
        source_execution_id: str | None,
        source_semantics_sha256: str,
        revision: int,
        parent_vocabulary_id: str | None,
        parent_authority_sha256: str | None,
        revision_reason: str | None,
        revision_source_ref: str | None,
        concepts: list[SemanticConceptDefinition],
        concept_type_state_domains: dict[str, list[Any]],
        concept_type_requirement_domains: dict[str, list[Any]],
        schema_version: str,
    ) -> dict[str, Any]:
        payload = {
            "task_run_id": task_run_id,
            "task_id": task_id,
            "source_plan_id": source_plan_id,
            "source_execution_id": source_execution_id,
            "source_semantics_sha256": source_semantics_sha256,
            "revision": revision,
            "parent_vocabulary_id": parent_vocabulary_id,
            "parent_authority_sha256": parent_authority_sha256,
            "concepts": [item.model_dump(mode="json") for item in concepts],
            "concept_type_state_domains": concept_type_state_domains,
            "concept_type_requirement_domains": concept_type_requirement_domains,
            "schema_version": schema_version,
        }
        if revision_reason is not None:
            payload["revision_reason"] = revision_reason
        if revision_source_ref is not None:
            payload["revision_source_ref"] = revision_source_ref
        return payload

    def compute_authority_sha256(
        self,
        *,
        task_run_id: str | None,
        task_id: str | None,
        source_plan_id: str | None,
        source_execution_id: str | None,
        source_semantics_sha256: str,
        revision: int,
        parent_vocabulary_id: str | None,
        parent_authority_sha256: str | None,
        revision_reason: str | None,
        revision_source_ref: str | None,
        concepts: list[SemanticConceptDefinition],
        concept_type_state_domains: dict[str, list[Any]],
        concept_type_requirement_domains: dict[str, list[Any]],
        schema_version: str,
    ) -> str:
        return self.stable_sha256(
            self.authority_payload(
                task_run_id=task_run_id,
                task_id=task_id,
                source_plan_id=source_plan_id,
                source_execution_id=source_execution_id,
                source_semantics_sha256=source_semantics_sha256,
                revision=revision,
                parent_vocabulary_id=parent_vocabulary_id,
                parent_authority_sha256=parent_authority_sha256,
                revision_reason=revision_reason,
                revision_source_ref=revision_source_ref,
                concepts=concepts,
                concept_type_state_domains=concept_type_state_domains,
                concept_type_requirement_domains=concept_type_requirement_domains,
                schema_version=schema_version,
            )
        )

    def verify(self, vocabulary: TaskSemanticVocabulary) -> bool:
        expected = self.compute_authority_sha256(
            task_run_id=vocabulary.task_run_id,
            task_id=vocabulary.task_id,
            source_plan_id=vocabulary.source_plan_id,
            source_execution_id=vocabulary.source_execution_id,
            source_semantics_sha256=vocabulary.source_semantics_sha256,
            revision=vocabulary.revision,
            parent_vocabulary_id=vocabulary.parent_vocabulary_id,
            parent_authority_sha256=vocabulary.parent_authority_sha256,
            revision_reason=vocabulary.revision_reason,
            revision_source_ref=vocabulary.revision_source_ref,
            concepts=vocabulary.concepts,
            concept_type_state_domains=vocabulary.concept_type_state_domains,
            concept_type_requirement_domains=vocabulary.concept_type_requirement_domains,
            schema_version=vocabulary.schema_version,
        )
        return expected == vocabulary.authority_sha256

    def governed_view(self, vocabulary: TaskSemanticVocabulary) -> dict[str, Any]:
        if not self.verify(vocabulary):
            raise ValueError("task_semantic_vocabulary_authority_invalid")
        concepts_by_type: dict[str, list[SemanticConceptDefinition]] = {}
        for concept in vocabulary.concepts:
            concepts_by_type.setdefault(concept.concept_type, []).append(concept)

        use_safety = {
            item.concept_id: list(item.allowed_states)
            for item in concepts_by_type.get("use_safety", [])
        }
        use_safety_requirements = {
            item.concept_id: list(item.requirement_states)
            for item in concepts_by_type.get("use_safety", [])
        }
        semantic_properties = [
            item
            for concept_type in (
                "epistemic_property",
                "behavioral_property",
                "structural_property",
                "relationship",
            )
            for item in concepts_by_type.get(concept_type, [])
        ]
        return {
            "vocabulary_id": vocabulary.vocabulary_id,
            "authority_sha256": vocabulary.authority_sha256,
            "revision": vocabulary.revision,
            "source_semantics_sha256": vocabulary.source_semantics_sha256,
            "use_safety_dimensions": sorted(use_safety),
            "use_safety_allowed_states": use_safety,
            "use_safety_requirement_states": use_safety_requirements,
            "downstream_use_identifiers": sorted(
                item.concept_id
                for item in concepts_by_type.get("downstream_use", [])
            ),
            "semantic_property_identifiers": sorted(
                item.concept_id for item in semantic_properties
            ),
            "semantic_property_allowed_states": {
                item.concept_id: list(item.allowed_states)
                for item in semantic_properties
            },
            "semantic_property_requirement_states": {
                item.concept_id: list(item.requirement_states)
                for item in semantic_properties
            },
            "capability_identifiers": sorted(
                item.concept_id for item in concepts_by_type.get("capability", [])
            ),
            "constraint_families": sorted(
                item.concept_id
                for item in concepts_by_type.get("constraint_family", [])
            ),
            "work_modes": sorted(
                item.concept_id for item in concepts_by_type.get("work_mode", [])
            ),
            "effect_identifiers": sorted(
                item.concept_id for item in concepts_by_type.get("effect", [])
            ),
            "evidence_domain_identifiers": sorted(
                item.concept_id
                for item in concepts_by_type.get("evidence_domain", [])
            ),
        }
