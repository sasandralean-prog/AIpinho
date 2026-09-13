from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from aipinho.schemas.semantics.task_semantic_vocabulary import (
    SemanticConceptDefinition,
    SemanticConceptProvenance,
    TaskSemanticVocabulary,
    TaskSemanticVocabularyCompilation,
)
from aipinho.services.semantics.system_semantic_vocabulary_service import (
    SystemSemanticVocabularyService,
)


class TaskSemanticVocabularyCompilerService:
    """Compiles a frozen task vocabulary from canonical, typed semantics."""

    VERSION = "task_semantic_vocabulary_compiler.v1"

    def __init__(
        self,
        *,
        system_vocabulary: SystemSemanticVocabularyService | None = None,
    ) -> None:
        self.system_vocabulary = system_vocabulary or SystemSemanticVocabularyService()

    def compile_for_run(self, *, run: Any) -> TaskSemanticVocabularyCompilation:
        plan = getattr(run, "plan", None)
        canonical = getattr(plan, "canonical_execution_plan", None)
        if canonical is None:
            return TaskSemanticVocabularyCompilation(
                status="insufficient_contract_evidence",
                reason_codes=["TASK_SEMANTIC_VOCABULARY_CANONICAL_PLAN_REQUIRED"],
            )

        plan_id = str(getattr(plan, "plan_id", "") or "") or None
        execution_id = str(getattr(canonical, "execution_id", "") or "") or None
        semantic_graph = dict(
            (getattr(canonical, "metadata", {}) or {}).get("semantic_intent_graph")
            or {}
        )
        source_payload = {
            "task_run_id": str(getattr(run, "run_id", "") or "") or None,
            "task_id": str(getattr(run, "task_id", "") or "") or None,
            "plan_id": plan_id,
            "execution_id": execution_id,
            "semantic_goal": getattr(canonical, "semantic_goal", None),
            "operation_kind": getattr(canonical, "operation_kind", None),
            "intent_map": dict(getattr(run, "intent_map", {}) or {}),
            "semantic_intent_graph": semantic_graph,
            "required_capabilities": list(
                getattr(canonical, "required_capabilities", []) or []
            ),
            "steps": [
                step.model_dump(mode="json")
                for step in list(getattr(canonical, "execution_steps", []) or [])
            ],
        }
        source_sha256 = self._sha256(source_payload)

        concepts = list(self.system_vocabulary.concepts())
        seen = {(item.concept_type, item.concept_id) for item in concepts}
        plan_ref = f"canonical_execution_plan:{execution_id or plan_id or 'unknown'}"

        capabilities = self._unique(
            [
                *list(getattr(run, "capabilities_required", []) or []),
                *list(getattr(canonical, "required_capabilities", []) or []),
                *[
                    capability
                    for step in list(getattr(canonical, "execution_steps", []) or [])
                    for capability in list(getattr(step, "required_capabilities", []) or [])
                ],
            ]
        )
        for capability in capabilities:
            self._append_task_concept(
                concepts,
                seen=seen,
                concept_id=capability,
                concept_type="capability",
                source_kind="canonical_execution_plan",
                source_ref=plan_ref,
                source_field="required_capabilities",
                source_sha256=source_sha256,
            )
        typed_containers = [
            ("intent_map", dict(getattr(run, "intent_map", {}) or {})),
            ("semantic_intent_graph", semantic_graph),
            ("canonical_metadata", dict(getattr(canonical, "metadata", {}) or {})),
        ]
        for container_name, container in typed_containers:
            for concept_id in self._list_values(
                container,
                ("allowed_downstream_uses", "required_downstream_uses", "downstream_uses"),
            ):
                self._append_task_concept(
                    concepts,
                    seen=seen,
                    concept_id=concept_id,
                    concept_type="downstream_use",
                    source_kind=(
                        "semantic_intent_graph"
                        if container_name == "semantic_intent_graph"
                        else "intent_map"
                        if container_name == "intent_map"
                        else "canonical_execution_plan"
                    ),
                    source_ref=plan_ref,
                    source_field=container_name,
                    source_sha256=source_sha256,
                )
            for concept_id in self._mapping_keys(
                container,
                ("semantic_properties", "required_semantic_properties"),
            ):
                self._append_task_concept(
                    concepts,
                    seen=seen,
                    concept_id=concept_id,
                    concept_type="epistemic_property",
                    source_kind=(
                        "semantic_intent_graph"
                        if container_name == "semantic_intent_graph"
                        else "intent_map"
                        if container_name == "intent_map"
                        else "canonical_execution_plan"
                    ),
                    source_ref=plan_ref,
                    source_field=container_name,
                    source_sha256=source_sha256,
                    allowed_states=self.system_vocabulary.concept_type_state_domains()[
                        "epistemic_property"
                    ],
                    requirement_states=self.system_vocabulary.concept_type_requirement_domains()[
                        "epistemic_property"
                    ],
                )

        concepts = sorted(
            concepts,
            key=lambda item: (item.scope, item.concept_type, item.concept_id),
        )
        authority_payload = {
            "task_run_id": source_payload["task_run_id"],
            "task_id": source_payload["task_id"],
            "source_plan_id": plan_id,
            "source_execution_id": execution_id,
            "source_semantics_sha256": source_sha256,
            "revision": 1,
            "parent_vocabulary_id": None,
            "parent_authority_sha256": None,
            "concepts": [item.model_dump(mode="json") for item in concepts],
            "concept_type_state_domains": self.system_vocabulary.concept_type_state_domains(),
            "concept_type_requirement_domains": self.system_vocabulary.concept_type_requirement_domains(),
            "schema_version": "task_semantic_vocabulary.v1",
        }
        authority_sha256 = self._sha256(authority_payload)
        vocabulary = TaskSemanticVocabulary(
            vocabulary_id=f"task_semantic_vocabulary_{authority_sha256[:24]}",
            task_run_id=source_payload["task_run_id"],
            task_id=source_payload["task_id"],
            source_plan_id=plan_id,
            source_execution_id=execution_id,
            source_semantics_sha256=source_sha256,
            concepts=concepts,
            concept_type_state_domains=self.system_vocabulary.concept_type_state_domains(),
            concept_type_requirement_domains=self.system_vocabulary.concept_type_requirement_domains(),
            authority_sha256=authority_sha256,
        )
        return TaskSemanticVocabularyCompilation(
            status="compiled",
            vocabulary=vocabulary,
            source_semantics_sha256=source_sha256,
        )
    def _append_task_concept(
        self,
        concepts: list[SemanticConceptDefinition],
        *,
        seen: set[tuple[str, str]],
        concept_id: str,
        concept_type: str,
        source_kind: str,
        source_ref: str,
        source_field: str,
        source_sha256: str,
        allowed_states: list[Any] | None = None,
        requirement_states: list[Any] | None = None,
    ) -> None:
        identifier = str(concept_id or "").strip()
        key = (concept_type, identifier)
        if not self._valid_identifier(identifier) or key in seen:
            return
        concepts.append(
            SemanticConceptDefinition(
                concept_id=identifier,
                concept_type=concept_type,
                scope="task",
                allowed_states=list(allowed_states or []),
                requirement_states=list(requirement_states or []),
                provenance=[
                    SemanticConceptProvenance(
                        source_kind=source_kind,
                        source_ref=source_ref,
                        source_field=source_field,
                        source_sha256=source_sha256,
                    )
                ],
            )
        )
        seen.add(key)

    def _list_values(
        self,
        container: dict[str, Any],
        fields: tuple[str, ...],
    ) -> list[str]:
        values: list[str] = []
        for field in fields:
            raw = container.get(field)
            if isinstance(raw, list):
                values.extend(str(item) for item in raw if str(item).strip())
        return self._unique(values)

    def _mapping_keys(
        self,
        container: dict[str, Any],
        fields: tuple[str, ...],
    ) -> list[str]:
        values: list[str] = []
        for field in fields:
            raw = container.get(field)
            if isinstance(raw, dict):
                values.extend(str(item) for item in raw if str(item).strip())
        return self._unique(values)

    def _valid_identifier(self, value: str) -> bool:
        return re.fullmatch(r"[a-z][a-z0-9_]*", value) is not None

    def _unique(self, values: list[Any]) -> list[str]:
        return list(
            dict.fromkeys(
                str(item).strip()
                for item in values
                if str(item).strip()
            )
        )

    def _sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()
