from __future__ import annotations

import hashlib
import json
import re

from aipinho.schemas.semantics.task_semantic_vocabulary import (
    SemanticConceptDefinition,
    SemanticConceptProvenance,
    TaskSemanticVocabulary,
    TaskSemanticVocabularyRevisionRequest,
    TaskSemanticVocabularyRevisionResult,
)
from aipinho.services.semantics.system_semantic_vocabulary_service import (
    SystemSemanticVocabularyService,
)


class TaskSemanticVocabularyRevisionService:
    """Applies additive, fail-closed revisions to frozen task vocabularies."""

    VERSION = "task_semantic_vocabulary_revision.v1"

    _TASK_REVISION_TYPES = {
        "epistemic_property",
        "behavioral_property",
        "structural_property",
        "relationship",
        "downstream_use",
        "evidence_domain",
    }

    def __init__(
        self,
        *,
        system_vocabulary: SystemSemanticVocabularyService | None = None,
    ) -> None:
        self.system_vocabulary = system_vocabulary or SystemSemanticVocabularyService()

    def revise(
        self,
        *,
        parent: TaskSemanticVocabulary,
        request: TaskSemanticVocabularyRevisionRequest,
    ) -> TaskSemanticVocabularyRevisionResult:
        if request.parent_vocabulary_id != parent.vocabulary_id:
            return self._rejected("TASK_SEMANTIC_VOCABULARY_PARENT_ID_MISMATCH")
        if request.parent_authority_sha256 != parent.authority_sha256:
            return self._rejected("TASK_SEMANTIC_VOCABULARY_PARENT_HASH_MISMATCH")
        if not request.reason.strip():
            return self._rejected("TASK_SEMANTIC_VOCABULARY_REVISION_REASON_REQUIRED")
        if not request.concepts_to_add:
            return self._rejected("TASK_SEMANTIC_VOCABULARY_REVISION_EMPTY")

        existing = {item.concept_id: item for item in parent.concepts}
        additions: list[SemanticConceptDefinition] = []
        seen_new: set[str] = set()
        for candidate in request.concepts_to_add:
            reason = self._validate_candidate(candidate, existing=existing, seen_new=seen_new)
            if reason:
                return self._rejected(reason)
            provenance = list(candidate.provenance)
            provenance.append(
                SemanticConceptProvenance(
                    source_kind="deterministic_gate",
                    source_ref=self.VERSION,
                    source_field="concepts_to_add",
                    source_sha256=parent.authority_sha256,
                )
            )
            additions.append(
                candidate.model_copy(
                    update={
                        "scope": "task",
                        "provenance": provenance,
                    },
                    deep=True,
                )
            )
            seen_new.add(candidate.concept_id)

        concepts = sorted(
            [*parent.concepts, *additions],
            key=lambda item: (item.scope, item.concept_type, item.concept_id),
        )
        authority_payload = {
            "task_run_id": parent.task_run_id,
            "task_id": parent.task_id,
            "source_plan_id": parent.source_plan_id,
            "source_execution_id": parent.source_execution_id,
            "source_semantics_sha256": parent.source_semantics_sha256,
            "revision": parent.revision + 1,
            "parent_vocabulary_id": parent.vocabulary_id,
            "parent_authority_sha256": parent.authority_sha256,
            "revision_reason": request.reason,
            "revision_source_ref": request.source_ref,
            "concepts": [item.model_dump(mode="json") for item in concepts],
            "concept_type_state_domains": parent.concept_type_state_domains,
            "concept_type_requirement_domains": parent.concept_type_requirement_domains,
            "schema_version": parent.schema_version,
        }
        authority_sha256 = self._sha256(authority_payload)
        revised = TaskSemanticVocabulary(
            vocabulary_id=f"task_semantic_vocabulary_{authority_sha256[:24]}",
            task_run_id=parent.task_run_id,
            task_id=parent.task_id,
            source_plan_id=parent.source_plan_id,
            source_execution_id=parent.source_execution_id,
            source_semantics_sha256=parent.source_semantics_sha256,
            revision=parent.revision + 1,
            parent_vocabulary_id=parent.vocabulary_id,
            parent_authority_sha256=parent.authority_sha256,
            revision_reason=request.reason,
            revision_source_ref=request.source_ref,
            concepts=concepts,
            concept_type_state_domains=dict(parent.concept_type_state_domains),
            concept_type_requirement_domains=dict(parent.concept_type_requirement_domains),
            authority_sha256=authority_sha256,
        )
        return TaskSemanticVocabularyRevisionResult(
            status="revised",
            vocabulary=revised,
        )

    def _validate_candidate(
        self,
        candidate: SemanticConceptDefinition,
        *,
        existing: dict[str, SemanticConceptDefinition],
        seen_new: set[str],
    ) -> str | None:
        identifier = str(candidate.concept_id or "").strip()
        if re.fullmatch(r"[a-z][a-z0-9_]*", identifier) is None:
            return "TASK_SEMANTIC_VOCABULARY_CONCEPT_ID_INVALID"
        if identifier in existing or identifier in seen_new:
            return "TASK_SEMANTIC_VOCABULARY_CONCEPT_ALREADY_DEFINED"
        if candidate.scope != "task":
            return "TASK_SEMANTIC_VOCABULARY_REVISION_SCOPE_INVALID"
        if candidate.concept_type not in self._TASK_REVISION_TYPES:
            return "TASK_SEMANTIC_VOCABULARY_REVISION_TYPE_NOT_ALLOWED"

        type_states = self.system_vocabulary.concept_type_state_domains().get(
            candidate.concept_type,
            [],
        )
        type_requirement_states = self.system_vocabulary.concept_type_requirement_domains().get(
            candidate.concept_type,
            [],
        )
        if candidate.allowed_states:
            if not type_states or any(value not in type_states for value in candidate.allowed_states):
                return "TASK_SEMANTIC_VOCABULARY_STATE_OUTSIDE_TYPE_DOMAIN"
        if candidate.requirement_states:
            if not candidate.allowed_states:
                return "TASK_SEMANTIC_VOCABULARY_REQUIREMENT_STATE_WITHOUT_DOMAIN"
            if any(value not in candidate.allowed_states for value in candidate.requirement_states):
                return "TASK_SEMANTIC_VOCABULARY_REQUIREMENT_STATE_OUTSIDE_CONCEPT_DOMAIN"
            if not type_requirement_states or any(
                value not in type_requirement_states
                for value in candidate.requirement_states
            ):
                return "TASK_SEMANTIC_VOCABULARY_REQUIREMENT_STATE_OUTSIDE_TYPE_DOMAIN"
        return None

    def _rejected(self, reason: str) -> TaskSemanticVocabularyRevisionResult:
        return TaskSemanticVocabularyRevisionResult(
            status="rejected",
            reason_codes=[reason],
        )

    def _sha256(self, payload: object) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()
