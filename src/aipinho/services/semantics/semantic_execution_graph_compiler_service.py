from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from aipinho.schemas.semantics.semantic_execution_graph import (
    SemanticDependencyEdge,
    SemanticExecutionGraph,
    SemanticWorkDecompositionCandidate,
    SemanticWorkDecompositionResult,
    SemanticWorkUnitContract,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.task_semantic_vocabulary_authority_service import (
    TaskSemanticVocabularyAuthorityService,
)


class SemanticExecutionGraphCompilerService:
    """Builds semantic work graphs without treating phase order as authority."""

    VERSION = "semantic_execution_graph_compiler.v1"
    MINIMUM_CONFIDENCE = 0.65

    def __init__(
        self,
        *,
        vocabulary_authority: TaskSemanticVocabularyAuthorityService | None = None,
        graph_authority: SemanticExecutionGraphAuthorityService | None = None,
    ) -> None:
        self.vocabulary_authority = (
            vocabulary_authority or TaskSemanticVocabularyAuthorityService()
        )
        self.graph_authority = (
            graph_authority or SemanticExecutionGraphAuthorityService()
        )

    def compile_structural_for_run(self, *, run: Any) -> SemanticWorkDecompositionResult:
        context, reason = self._context(run)
        if reason:
            return self._insufficient(reason)
        assert context is not None

        work_units: list[SemanticWorkUnitContract] = []
        reason_codes: list[str] = []
        for step in context["steps"]:
            explicit_modes = self._string_list(
                (getattr(step, "metadata", {}) or {}).get("work_modes")
            )
            invalid = [
                mode
                for mode in explicit_modes
                if mode not in context["work_modes"]
            ]
            if invalid:
                return self._insufficient(
                    "SEMANTIC_WORK_GRAPH_EXPLICIT_WORK_MODE_UNGOVERNED"
                )
            requested_effects = self._string_list(
                (getattr(step, "metadata", {}) or {}).get("requested_effects")
            )
            prohibited_effects = self._string_list(
                (getattr(step, "metadata", {}) or {}).get("prohibited_effects")
            )
            if any(
                effect not in context["effects"]
                for effect in [*requested_effects, *prohibited_effects]
            ):
                return self._insufficient(
                    "SEMANTIC_WORK_GRAPH_EXPLICIT_EFFECT_UNGOVERNED"
                )
            capabilities = list(getattr(step, "required_capabilities", []) or [])
            if any(
                capability not in context["capabilities"]
                for capability in capabilities
            ):
                return self._insufficient(
                    "SEMANTIC_WORK_GRAPH_CAPABILITY_UNGOVERNED"
                )
            step_id = str(getattr(step, "step_id", "") or "")
            if not step_id:
                return self._insufficient(
                    "SEMANTIC_WORK_GRAPH_SOURCE_STEP_ID_REQUIRED"
                )
            unit = self._work_unit(
                context=context,
                source_step_ids=[step_id],
                semantic_goal=str(
                    (getattr(step, "metadata", {}) or {}).get("semantic_goal")
                    or getattr(step, "action", "")
                    or getattr(step, "step_type", "")
                    or step_id
                ),
                work_modes=explicit_modes,
                classification_status="explicit" if explicit_modes else "unknown",
                required_capabilities=capabilities,
                requested_effects=requested_effects,
                prohibited_effects=prohibited_effects,
            )
            if not explicit_modes:
                reason_codes.append(
                    f"semantic_work_mode_unknown:{unit.work_unit_id}"
                )
            work_units.append(unit)

        edges, edge_reason = self._explicit_dependency_edges(
            context=context,
            work_units=work_units,
        )
        if edge_reason:
            return self._insufficient(edge_reason)
        status = "ready" if not reason_codes else "partial"
        graph = self._freeze_graph(
            context=context,
            work_units=work_units,
            edges=edges,
            status=status,
            reason_codes=reason_codes,
        )
        return SemanticWorkDecompositionResult(
            status="accepted",
            graph=graph,
            provenance={
                "authority": "deterministic_semantic_graph_gate",
                "compiler": self.VERSION,
                "mode": "structural",
            },
        )
    def compile_candidate_for_run(
        self,
        *,
        run: Any,
        candidate: SemanticWorkDecompositionCandidate,
        provenance: dict[str, Any] | None = None,
    ) -> SemanticWorkDecompositionResult:
        context, reason = self._context(run)
        if reason:
            return self._insufficient(reason, provenance=provenance)
        assert context is not None

        if candidate.confidence < self.MINIMUM_CONFIDENCE:
            return self._insufficient(
                "SEMANTIC_WORK_DECOMPOSITION_CONFIDENCE_INSUFFICIENT",
                provenance=provenance,
            )
        if not candidate.rationale.strip():
            return self._insufficient(
                "SEMANTIC_WORK_DECOMPOSITION_RATIONALE_REQUIRED",
                provenance=provenance,
            )
        if not candidate.work_units:
            return self._insufficient(
                "SEMANTIC_WORK_DECOMPOSITION_UNITS_REQUIRED",
                provenance=provenance,
            )

        known_step_ids = set(context["steps_by_id"])
        unit_keys: set[str] = set()
        coverage: dict[str, str] = {}
        canonical_units: list[SemanticWorkUnitContract] = []
        key_to_unit: dict[str, SemanticWorkUnitContract] = {}

        for proposed in candidate.work_units:
            key = proposed.unit_key.strip()
            if (
                re.fullmatch(r"[a-z][a-z0-9_]*", key) is None
                or key in unit_keys
            ):
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_UNIT_KEY_INVALID",
                    provenance=provenance,
                )
            unit_keys.add(key)
            source_step_ids = list(dict.fromkeys(proposed.source_step_ids))
            if not source_step_ids:
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_SOURCE_STEPS_REQUIRED",
                    provenance=provenance,
                )
            if any(step_id not in known_step_ids for step_id in source_step_ids):
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_SOURCE_STEP_UNKNOWN",
                    provenance=provenance,
                )
            for step_id in source_step_ids:
                if step_id in coverage:
                    return self._insufficient(
                        "SEMANTIC_WORK_DECOMPOSITION_SOURCE_STEP_DUPLICATED",
                        provenance=provenance,
                    )
                coverage[step_id] = key

            if not proposed.work_modes:
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_WORK_MODE_REQUIRED",
                    provenance=provenance,
                )
            if any(mode not in context["work_modes"] for mode in proposed.work_modes):
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_WORK_MODE_UNGOVERNED",
                    provenance=provenance,
                )

            canonical_capabilities = self._capabilities_for_steps(
                context,
                source_step_ids,
            )
            if set(proposed.required_capabilities) != set(canonical_capabilities):
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_CAPABILITY_MISMATCH",
                    provenance=provenance,
                )
            if any(
                effect not in context["effects"]
                for effect in [
                    *proposed.requested_effects,
                    *proposed.prohibited_effects,
                ]
            ):
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_EFFECT_UNGOVERNED",
                    provenance=provenance,
                )
            if not proposed.semantic_goal.strip():
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_GOAL_REQUIRED",
                    provenance=provenance,
                )

            unit = self._work_unit(
                context=context,
                source_step_ids=source_step_ids,
                semantic_goal=proposed.semantic_goal.strip(),
                work_modes=list(dict.fromkeys(proposed.work_modes)),
                classification_status="interpreted",
                required_capabilities=canonical_capabilities,
                requested_effects=list(dict.fromkeys(proposed.requested_effects)),
                prohibited_effects=list(dict.fromkeys(proposed.prohibited_effects)),
            )
            canonical_units.append(unit)
            key_to_unit[key] = unit

        if set(coverage) != known_step_ids:
            return self._insufficient(
                "SEMANTIC_WORK_DECOMPOSITION_SOURCE_STEP_COVERAGE_INCOMPLETE",
                provenance=provenance,
            )
        edges: list[SemanticDependencyEdge] = []
        edge_keys: set[tuple[str, str, str]] = set()
        for proposed_edge in candidate.edges:
            producer = key_to_unit.get(proposed_edge.producer_unit_key)
            consumer = key_to_unit.get(proposed_edge.consumer_unit_key)
            if producer is None or consumer is None:
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_EDGE_UNIT_UNKNOWN",
                    provenance=provenance,
                )
            if producer.work_unit_id == consumer.work_unit_id:
                return self._insufficient(
                    "SEMANTIC_WORK_DECOMPOSITION_SELF_EDGE_INVALID",
                    provenance=provenance,
                )
            edge_key = (
                producer.work_unit_id,
                consumer.work_unit_id,
                proposed_edge.relation,
            )
            if edge_key in edge_keys:
                continue
            edge_keys.add(edge_key)
            edges.append(
                self._edge(
                    context=context,
                    producer_work_unit_id=producer.work_unit_id,
                    consumer_work_unit_id=consumer.work_unit_id,
                    relation=proposed_edge.relation,
                    required=proposed_edge.required,
                    source_refs=["semantic_work_decomposition_candidate"],
                )
            )

        missing_explicit = self._missing_explicit_dependencies(
            context=context,
            coverage=coverage,
            key_to_unit=key_to_unit,
            edges=edges,
        )
        if missing_explicit:
            return self._insufficient(
                "SEMANTIC_WORK_DECOMPOSITION_EXPLICIT_DEPENDENCY_MISSING",
                provenance=provenance,
            )
        if not self._is_acyclic(canonical_units, edges):
            return self._insufficient(
                "SEMANTIC_WORK_DECOMPOSITION_CYCLE_DETECTED",
                provenance=provenance,
            )

        graph = self._freeze_graph(
            context=context,
            work_units=canonical_units,
            edges=edges,
            status="ready",
            reason_codes=[],
        )
        return SemanticWorkDecompositionResult(
            status="accepted",
            graph=graph,
            candidate=candidate.model_dump(mode="json"),
            provenance={
                **dict(provenance or {}),
                "authority": "deterministic_semantic_graph_gate",
                "compiler": self.VERSION,
                "mode": "interpreted",
            },
        )

    def _context(self, run: Any) -> tuple[dict[str, Any] | None, str | None]:
        plan = getattr(run, "plan", None)
        canonical = getattr(plan, "canonical_execution_plan", None)
        vocabulary = getattr(plan, "task_semantic_vocabulary", None)
        if canonical is None:
            return None, "SEMANTIC_WORK_GRAPH_CANONICAL_PLAN_REQUIRED"
        if vocabulary is None:
            return None, "SEMANTIC_WORK_GRAPH_TASK_VOCABULARY_REQUIRED"
        if not self.vocabulary_authority.verify(vocabulary):
            return None, "SEMANTIC_WORK_GRAPH_TASK_VOCABULARY_AUTHORITY_INVALID"
        steps = list(getattr(canonical, "execution_steps", []) or [])
        if not steps:
            return None, "SEMANTIC_WORK_GRAPH_CANONICAL_STEPS_REQUIRED"
        view = self.vocabulary_authority.governed_view(vocabulary)
        steps_by_id = {
            str(getattr(step, "step_id", "") or ""): step
            for step in steps
            if str(getattr(step, "step_id", "") or "")
        }
        if len(steps_by_id) != len(steps):
            return None, "SEMANTIC_WORK_GRAPH_SOURCE_STEP_IDS_INVALID"
        source_semantics_sha256 = self.graph_authority.stable_sha256(
            {
                "canonical_execution_plan": canonical.model_dump(mode="json"),
                "vocabulary_binding": vocabulary.binding().model_dump(mode="json"),
            }
        )
        return {
            "run": run,
            "plan": plan,
            "canonical": canonical,
            "vocabulary": vocabulary,
            "vocabulary_binding": vocabulary.binding(),
            "view": view,
            "steps": steps,
            "steps_by_id": steps_by_id,
            "work_modes": set(view.get("work_modes") or []),
            "effects": set(view.get("effect_identifiers") or []),
            "capabilities": set(view.get("capability_identifiers") or []),
            "source_semantics_sha256": source_semantics_sha256,
        }, None
    def _work_unit(
        self,
        *,
        context: dict[str, Any],
        source_step_ids: list[str],
        semantic_goal: str,
        work_modes: list[str],
        classification_status: str,
        required_capabilities: list[str],
        requested_effects: list[str],
        prohibited_effects: list[str],
    ) -> SemanticWorkUnitContract:
        step_ids = sorted(dict.fromkeys(source_step_ids))
        steps = [context["steps_by_id"][step_id] for step_id in step_ids]
        identity_sha = self.graph_authority.stable_sha256(
            {
                "task_run_id": str(getattr(context["run"], "run_id", "") or ""),
                "vocabulary_authority_sha256": context[
                    "vocabulary_binding"
                ].authority_sha256,
                "source_step_ids": step_ids,
            }
        )
        source_inputs: dict[str, Any] = {}
        expected_outputs: list[str] = []
        for step in steps:
            step_id = str(getattr(step, "step_id", "") or "")
            inputs = dict(getattr(step, "inputs", {}) or {})
            if inputs:
                source_inputs[step_id] = inputs
            expected_outputs.extend(
                str(item)
                for item in list(getattr(step, "expected_outputs", []) or [])
                if str(item)
            )
        return SemanticWorkUnitContract(
            work_unit_id=f"semantic_work_unit_{identity_sha[:24]}",
            source_step_ids=step_ids,
            semantic_goal=semantic_goal,
            work_modes=list(work_modes),
            classification_status=classification_status,  # type: ignore[arg-type]
            required_capabilities=list(required_capabilities),
            requested_effects=list(requested_effects),
            prohibited_effects=list(prohibited_effects),
            expected_outputs=list(dict.fromkeys(expected_outputs)),
            source_inputs=source_inputs,
            required=any(bool(getattr(step, "required", True)) for step in steps),
            contains_side_effect=any(
                bool(getattr(step, "side_effect", False)) for step in steps
            ),
            vocabulary_binding=context["vocabulary_binding"],
        )

    def _explicit_dependency_edges(
        self,
        *,
        context: dict[str, Any],
        work_units: list[SemanticWorkUnitContract],
    ) -> tuple[list[SemanticDependencyEdge], str | None]:
        step_to_unit = {
            step_id: unit
            for unit in work_units
            for step_id in unit.source_step_ids
        }
        edges: list[SemanticDependencyEdge] = []
        seen: set[tuple[str, str]] = set()
        for step in context["steps"]:
            target_step_id = str(getattr(step, "step_id", "") or "")
            target = step_to_unit[target_step_id]
            for source_step_id in list(getattr(step, "depends_on", []) or []):
                source = step_to_unit.get(str(source_step_id))
                if source is None:
                    return [], "SEMANTIC_WORK_GRAPH_EXPLICIT_DEPENDENCY_UNKNOWN"
                if source.work_unit_id == target.work_unit_id:
                    continue
                key = (source.work_unit_id, target.work_unit_id)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    self._edge(
                        context=context,
                        producer_work_unit_id=source.work_unit_id,
                        consumer_work_unit_id=target.work_unit_id,
                        relation="ordering_constraint",
                        required=True,
                        source_refs=[
                            f"canonical_execution_step:{target_step_id}:depends_on:{source_step_id}"
                        ],
                    )
                )
        if not self._is_acyclic(work_units, edges):
            return [], "SEMANTIC_WORK_GRAPH_EXPLICIT_DEPENDENCY_CYCLE"
        return edges, None

    def _missing_explicit_dependencies(
        self,
        *,
        context: dict[str, Any],
        coverage: dict[str, str],
        key_to_unit: dict[str, SemanticWorkUnitContract],
        edges: list[SemanticDependencyEdge],
    ) -> list[tuple[str, str]]:
        pairs = {
            (edge.producer_work_unit_id, edge.consumer_work_unit_id)
            for edge in edges
        }
        missing: list[tuple[str, str]] = []
        for step in context["steps"]:
            target_step_id = str(getattr(step, "step_id", "") or "")
            target_key = coverage[target_step_id]
            target_unit = key_to_unit[target_key]
            for source_step_id in list(getattr(step, "depends_on", []) or []):
                source_key = coverage.get(str(source_step_id))
                if source_key is None:
                    missing.append((str(source_step_id), target_step_id))
                    continue
                source_unit = key_to_unit[source_key]
                if source_unit.work_unit_id == target_unit.work_unit_id:
                    continue
                if (source_unit.work_unit_id, target_unit.work_unit_id) not in pairs:
                    missing.append((str(source_step_id), target_step_id))
        return missing
    def _capabilities_for_steps(
        self,
        context: dict[str, Any],
        source_step_ids: list[str],
    ) -> list[str]:
        return list(
            dict.fromkeys(
                str(capability)
                for step_id in source_step_ids
                for capability in list(
                    getattr(
                        context["steps_by_id"][step_id],
                        "required_capabilities",
                        [],
                    )
                    or []
                )
                if str(capability)
            )
        )

    def _edge(
        self,
        *,
        context: dict[str, Any],
        producer_work_unit_id: str,
        consumer_work_unit_id: str,
        relation: str,
        required: bool,
        source_refs: list[str],
    ) -> SemanticDependencyEdge:
        edge_sha = self.graph_authority.stable_sha256(
            {
                "task_run_id": str(getattr(context["run"], "run_id", "") or ""),
                "producer": producer_work_unit_id,
                "consumer": consumer_work_unit_id,
                "relation": relation,
            }
        )
        return SemanticDependencyEdge(
            edge_id=f"semantic_edge_{edge_sha[:24]}",
            producer_work_unit_id=producer_work_unit_id,
            consumer_work_unit_id=consumer_work_unit_id,
            relation=relation,  # type: ignore[arg-type]
            required=required,
            source_refs=list(source_refs),
        )

    def _freeze_graph(
        self,
        *,
        context: dict[str, Any],
        work_units: list[SemanticWorkUnitContract],
        edges: list[SemanticDependencyEdge],
        status: str,
        reason_codes: list[str],
    ) -> SemanticExecutionGraph:
        run = context["run"]
        plan = context["plan"]
        canonical = context["canonical"]
        schema_version = "semantic_execution_graph.v1"
        kwargs = {
            "task_run_id": str(getattr(run, "run_id", "") or ""),
            "task_id": str(getattr(run, "task_id", "") or "") or None,
            "source_plan_id": str(getattr(plan, "plan_id", "") or ""),
            "source_execution_id": str(
                getattr(canonical, "execution_id", "") or ""
            ),
            "source_semantics_sha256": context["source_semantics_sha256"],
            "vocabulary_binding": context["vocabulary_binding"],
            "work_units": work_units,
            "edges": edges,
            "status": status,
            "reason_codes": list(reason_codes),
            "schema_version": schema_version,
        }
        authority_sha256 = self.graph_authority.compute_authority_sha256(
            **kwargs
        )
        return SemanticExecutionGraph(
            semantic_graph_id=f"semantic_execution_graph_{authority_sha256[:24]}",
            authority_sha256=authority_sha256,
            **kwargs,
        )

    def _is_acyclic(
        self,
        work_units: list[SemanticWorkUnitContract],
        edges: list[SemanticDependencyEdge],
    ) -> bool:
        node_ids = {item.work_unit_id for item in work_units}
        indegree = {node_id: 0 for node_id in node_ids}
        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            if (
                edge.producer_work_unit_id not in node_ids
                or edge.consumer_work_unit_id not in node_ids
            ):
                return False
            adjacency[edge.producer_work_unit_id].append(
                edge.consumer_work_unit_id
            )
            indegree[edge.consumer_work_unit_id] += 1
        ready = [node_id for node_id, degree in indegree.items() if degree == 0]
        visited = 0
        while ready:
            node_id = ready.pop()
            visited += 1
            for target in adjacency[node_id]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
        return visited == len(node_ids)

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(str(item) for item in value if str(item)))

    def _insufficient(
        self,
        reason: str,
        *,
        provenance: dict[str, Any] | None = None,
    ) -> SemanticWorkDecompositionResult:
        return SemanticWorkDecompositionResult(
            status="insufficient_evidence",
            reason_code=reason,
            provenance=dict(provenance or {}),
        )
