from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from aipinho.schemas.semantics.semantic_execution_graph import (
    SemanticDependencyEdge,
    SemanticExecutionGraph,
    SemanticWorkUnitContract,
)
from aipinho.schemas.semantics.semantic_graph_revision import (
    SemanticGraphRevision,
    SemanticGraphRevisionApplication,
    SemanticGraphRevisionEdgeAddition,
    SemanticGraphRevisionProposal,
    SemanticGraphRevisionWorkUnitAddition,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.semantic_graph_revision_authority_service import (
    SemanticGraphRevisionAuthorityService,
)
from aipinho.services.semantics.task_semantic_vocabulary_authority_service import (
    TaskSemanticVocabularyAuthorityService,
)


class SemanticGraphRevisionService:
    """Applies explicit revisions by producing a new immutable graph snapshot."""

    VERSION = "semantic_graph_revision.v1"

    def __init__(
        self,
        *,
        graph_authority: SemanticExecutionGraphAuthorityService | None = None,
        vocabulary_authority: TaskSemanticVocabularyAuthorityService | None = None,
        revision_authority: SemanticGraphRevisionAuthorityService | None = None,
    ) -> None:
        self.graph_authority = (
            graph_authority or SemanticExecutionGraphAuthorityService()
        )
        self.vocabulary_authority = (
            vocabulary_authority or TaskSemanticVocabularyAuthorityService()
        )
        self.revision_authority = (
            revision_authority or SemanticGraphRevisionAuthorityService()
        )

    def apply(
        self,
        *,
        run: Any,
        proposal: SemanticGraphRevisionProposal,
    ) -> SemanticGraphRevisionApplication:
        plan = getattr(run, "plan", None)
        parent = getattr(plan, "semantic_execution_graph", None)
        vocabulary = getattr(plan, "task_semantic_vocabulary", None)
        if parent is None:
            return self._insufficient("GRAPH_REVISION_PARENT_GRAPH_REQUIRED")
        if not self.graph_authority.verify(parent):
            return self._insufficient(
                "GRAPH_REVISION_PARENT_GRAPH_AUTHORITY_INVALID"
            )
        if vocabulary is None:
            return self._insufficient("GRAPH_REVISION_VOCABULARY_REQUIRED")
        if not self.vocabulary_authority.verify(vocabulary):
            return self._insufficient(
                "GRAPH_REVISION_VOCABULARY_AUTHORITY_INVALID"
            )
        if parent.vocabulary_binding != vocabulary.binding():
            return self._insufficient(
                "GRAPH_REVISION_VOCABULARY_BINDING_MISMATCH"
            )
        if (
            proposal.parent_graph_id != parent.semantic_graph_id
            or proposal.parent_graph_authority_sha256
            != parent.authority_sha256
        ):
            return self._blocked("GRAPH_REVISION_PARENT_BINDING_MISMATCH")
        if proposal.revision_number < 1:
            return self._blocked("GRAPH_REVISION_NUMBER_INVALID")
        if not proposal.reason.strip():
            return self._blocked("GRAPH_REVISION_REASON_REQUIRED")
        if not proposal.provenance:
            return self._blocked("GRAPH_REVISION_PROVENANCE_REQUIRED")
        if not any(
            [
                proposal.add_work_units,
                proposal.add_edges,
                proposal.remove_edge_ids,
                proposal.remove_work_unit_ids,
            ]
        ):
            return self._blocked("GRAPH_REVISION_NO_CHANGES")

        context, reason = self._validate_and_prepare(
            parent=parent,
            vocabulary=vocabulary,
            proposal=proposal,
        )
        if reason:
            return self._blocked(reason)
        assert context is not None

        child = self._build_child(
            parent=parent,
            proposal=proposal,
            context=context,
        )
        revision = self._build_revision(
            parent=parent,
            child=child,
            proposal=proposal,
            context=context,
        )
        return SemanticGraphRevisionApplication(
            status="applied",
            revision=revision,
            child_graph=child,
        )

    def _validate_and_prepare(
        self,
        *,
        parent: SemanticExecutionGraph,
        vocabulary: Any,
        proposal: SemanticGraphRevisionProposal,
    ) -> tuple[dict[str, Any] | None, str | None]:
        work_units = {item.work_unit_id: item for item in parent.work_units}
        edges = {item.edge_id: item for item in parent.edges}
        view = self.vocabulary_authority.governed_view(vocabulary)

        if len(set(proposal.remove_edge_ids)) != len(proposal.remove_edge_ids):
            return None, "GRAPH_REVISION_DUPLICATE_EDGE_REMOVAL"
        if len(set(proposal.remove_work_unit_ids)) != len(
            proposal.remove_work_unit_ids
        ):
            return None, "GRAPH_REVISION_DUPLICATE_WORK_UNIT_REMOVAL"
        if any(edge_id not in edges for edge_id in proposal.remove_edge_ids):
            return None, "GRAPH_REVISION_REMOVE_EDGE_UNKNOWN"
        if any(
            unit_id not in work_units
            for unit_id in proposal.remove_work_unit_ids
        ):
            return None, "GRAPH_REVISION_REMOVE_WORK_UNIT_UNKNOWN"

        removed_edge_ids = set(proposal.remove_edge_ids)
        removed_unit_ids = set(proposal.remove_work_unit_ids)
        for unit_id in removed_unit_ids:
            incident = {
                edge.edge_id
                for edge in parent.edges
                if edge.producer_work_unit_id == unit_id
                or edge.consumer_work_unit_id == unit_id
            }
            if not incident.issubset(removed_edge_ids):
                return None, "GRAPH_REVISION_WORK_UNIT_HAS_UNREMOVED_EDGES"

        addition_keys: set[str] = set()
        added_units: dict[str, SemanticWorkUnitContract] = {}
        for addition in proposal.add_work_units:
            if (
                re.fullmatch(r"[a-z][a-z0-9_]*", addition.addition_key)
                is None
                or addition.addition_key in addition_keys
            ):
                return None, "GRAPH_REVISION_WORK_UNIT_ADDITION_KEY_INVALID"
            addition_keys.add(addition.addition_key)
            reason = self._validate_work_unit_addition(addition, view=view)
            if reason:
                return None, reason
            unit = self._materialize_work_unit(
                parent=parent,
                proposal=proposal,
                addition=addition,
            )
            added_units[addition.addition_key] = unit

        remaining_units = {
            unit_id: unit
            for unit_id, unit in work_units.items()
            if unit_id not in removed_unit_ids
        }
        final_units = {
            **remaining_units,
            **{unit.work_unit_id: unit for unit in added_units.values()},
        }
        if len(final_units) != len(remaining_units) + len(added_units):
            return None, "GRAPH_REVISION_WORK_UNIT_ID_COLLISION"

        seen_source_steps: dict[str, str] = {}
        for unit in final_units.values():
            for step_id in unit.source_step_ids:
                if step_id in seen_source_steps:
                    return None, "GRAPH_REVISION_SOURCE_STEP_DUPLICATED"
                seen_source_steps[step_id] = unit.work_unit_id

        edge_addition_keys: set[str] = set()
        added_edges: dict[str, SemanticDependencyEdge] = {}
        final_existing_edges = {
            edge_id: edge
            for edge_id, edge in edges.items()
            if edge_id not in removed_edge_ids
        }
        existing_edge_signatures = {
            (
                edge.producer_work_unit_id,
                edge.consumer_work_unit_id,
                edge.relation,
            )
            for edge in final_existing_edges.values()
        }
        for addition in proposal.add_edges:
            if (
                re.fullmatch(r"[a-z][a-z0-9_]*", addition.addition_key)
                is None
                or addition.addition_key in edge_addition_keys
            ):
                return None, "GRAPH_REVISION_EDGE_ADDITION_KEY_INVALID"
            edge_addition_keys.add(addition.addition_key)
            edge, reason = self._materialize_edge(
                parent=parent,
                proposal=proposal,
                addition=addition,
                existing_units=remaining_units,
                added_units=added_units,
            )
            if reason:
                return None, reason
            assert edge is not None
            signature = (
                edge.producer_work_unit_id,
                edge.consumer_work_unit_id,
                edge.relation,
            )
            if signature in existing_edge_signatures:
                return None, "GRAPH_REVISION_DUPLICATE_EDGE"
            existing_edge_signatures.add(signature)
            added_edges[addition.addition_key] = edge

        final_edges = [
            *final_existing_edges.values(),
            *added_edges.values(),
        ]
        if not self._is_acyclic(list(final_units.values()), final_edges):
            return None, "GRAPH_REVISION_CYCLE_DETECTED"

        return {
            "view": view,
            "remaining_units": remaining_units,
            "added_units": added_units,
            "final_units": final_units,
            "final_existing_edges": final_existing_edges,
            "added_edges": added_edges,
            "final_edges": final_edges,
            "removed_edge_ids": removed_edge_ids,
            "removed_unit_ids": removed_unit_ids,
        }, None

    def _validate_work_unit_addition(
        self,
        addition: SemanticGraphRevisionWorkUnitAddition,
        *,
        view: dict[str, Any],
    ) -> str | None:
        if not addition.semantic_goal.strip():
            return "GRAPH_REVISION_WORK_UNIT_GOAL_REQUIRED"
        if not addition.source_step_ids:
            return "GRAPH_REVISION_SOURCE_STEP_REQUIRED"
        if len(set(addition.source_step_ids)) != len(addition.source_step_ids):
            return "GRAPH_REVISION_SOURCE_STEP_DUPLICATED"
        governed_modes = set(view.get("work_modes") or [])
        if any(mode not in governed_modes for mode in addition.work_modes):
            return "GRAPH_REVISION_WORK_MODE_UNGOVERNED"
        governed_capabilities = set(view.get("capability_identifiers") or [])
        if any(
            capability not in governed_capabilities
            for capability in addition.required_capabilities
        ):
            return "GRAPH_REVISION_CAPABILITY_UNGOVERNED"
        governed_effects = set(view.get("effect_identifiers") or [])
        if any(
            effect not in governed_effects
            for effect in [
                *addition.requested_effects,
                *addition.prohibited_effects,
            ]
        ):
            return "GRAPH_REVISION_EFFECT_UNGOVERNED"
        return None

    def _materialize_work_unit(
        self,
        *,
        parent: SemanticExecutionGraph,
        proposal: SemanticGraphRevisionProposal,
        addition: SemanticGraphRevisionWorkUnitAddition,
    ) -> SemanticWorkUnitContract:
        identity_sha = self.graph_authority.stable_sha256(
            {
                "parent_graph_authority_sha256": parent.authority_sha256,
                "revision_number": proposal.revision_number,
                "addition_key": addition.addition_key,
                "addition": addition.model_dump(mode="json"),
            }
        )
        return SemanticWorkUnitContract(
            work_unit_id=f"semantic_work_unit_{identity_sha[:24]}",
            source_step_ids=list(addition.source_step_ids),
            semantic_goal=addition.semantic_goal.strip(),
            work_modes=list(dict.fromkeys(addition.work_modes)),
            classification_status=addition.classification_status,
            required_capabilities=list(
                dict.fromkeys(addition.required_capabilities)
            ),
            requested_effects=list(
                dict.fromkeys(addition.requested_effects)
            ),
            prohibited_effects=list(
                dict.fromkeys(addition.prohibited_effects)
            ),
            expected_outputs=list(
                dict.fromkeys(addition.expected_outputs)
            ),
            source_inputs=dict(addition.source_inputs),
            required=addition.required,
            contains_side_effect=addition.contains_side_effect,
            vocabulary_binding=parent.vocabulary_binding,
        )

    def _materialize_edge(
        self,
        *,
        parent: SemanticExecutionGraph,
        proposal: SemanticGraphRevisionProposal,
        addition: SemanticGraphRevisionEdgeAddition,
        existing_units: dict[str, SemanticWorkUnitContract],
        added_units: dict[str, SemanticWorkUnitContract],
    ) -> tuple[SemanticDependencyEdge | None, str | None]:
        producer = self._resolve_unit_ref(
            addition.producer_ref,
            existing_units=existing_units,
            added_units=added_units,
        )
        consumer = self._resolve_unit_ref(
            addition.consumer_ref,
            existing_units=existing_units,
            added_units=added_units,
        )
        if producer is None or consumer is None:
            return None, "GRAPH_REVISION_EDGE_UNIT_UNKNOWN"
        if producer.work_unit_id == consumer.work_unit_id:
            return None, "GRAPH_REVISION_SELF_EDGE_INVALID"
        edge_sha = self.graph_authority.stable_sha256(
            {
                "parent_graph_authority_sha256": parent.authority_sha256,
                "revision_number": proposal.revision_number,
                "addition_key": addition.addition_key,
                "producer_work_unit_id": producer.work_unit_id,
                "consumer_work_unit_id": consumer.work_unit_id,
                "relation": addition.relation,
                "required": addition.required,
            }
        )
        return SemanticDependencyEdge(
            edge_id=f"semantic_edge_{edge_sha[:24]}",
            producer_work_unit_id=producer.work_unit_id,
            consumer_work_unit_id=consumer.work_unit_id,
            relation=addition.relation,
            required=addition.required,
            source_refs=list(
                dict.fromkeys(
                    [
                        *addition.source_refs,
                        f"semantic_graph_revision:{proposal.proposal_id}",
                    ]
                )
            ),
        ), None

    def _resolve_unit_ref(
        self,
        ref: str,
        *,
        existing_units: dict[str, SemanticWorkUnitContract],
        added_units: dict[str, SemanticWorkUnitContract],
    ) -> SemanticWorkUnitContract | None:
        if ref.startswith("addition:"):
            return added_units.get(ref.split(":", 1)[1])
        return existing_units.get(ref)

    def _build_child(
        self,
        *,
        parent: SemanticExecutionGraph,
        proposal: SemanticGraphRevisionProposal,
        context: dict[str, Any],
    ) -> SemanticExecutionGraph:
        intent_sha = self.revision_authority.compute_intent_sha256(proposal)
        child_source_semantics_sha256 = self.graph_authority.stable_sha256(
            {
                "parent_source_semantics_sha256": (
                    parent.source_semantics_sha256
                ),
                "parent_graph_authority_sha256": parent.authority_sha256,
                "revision_intent_sha256": intent_sha,
            }
        )
        work_units = sorted(
            context["final_units"].values(),
            key=lambda item: item.work_unit_id,
        )
        edges = sorted(
            context["final_edges"],
            key=lambda item: item.edge_id,
        )
        unknown_units = [
            unit.work_unit_id
            for unit in work_units
            if unit.classification_status == "unknown"
        ]
        status = "partial" if unknown_units else "ready"
        reason_codes = [
            f"semantic_work_mode_unknown:{unit_id}"
            for unit_id in unknown_units
        ]
        schema_version = parent.schema_version
        kwargs = {
            "task_run_id": parent.task_run_id,
            "task_id": parent.task_id,
            "source_plan_id": parent.source_plan_id,
            "source_execution_id": parent.source_execution_id,
            "source_semantics_sha256": child_source_semantics_sha256,
            "vocabulary_binding": parent.vocabulary_binding,
            "work_units": work_units,
            "edges": edges,
            "status": status,
            "reason_codes": reason_codes,
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

    def _build_revision(
        self,
        *,
        parent: SemanticExecutionGraph,
        child: SemanticExecutionGraph,
        proposal: SemanticGraphRevisionProposal,
        context: dict[str, Any],
    ) -> SemanticGraphRevision:
        intent_sha = self.revision_authority.compute_intent_sha256(proposal)
        revision = SemanticGraphRevision(
            revision_id="pending",
            revision_number=proposal.revision_number,
            parent_revision_id=proposal.parent_revision_id,
            parent_graph_id=parent.semantic_graph_id,
            parent_graph_authority_sha256=parent.authority_sha256,
            child_graph_id=child.semantic_graph_id,
            child_graph_authority_sha256=child.authority_sha256,
            revision_intent_sha256=intent_sha,
            reason=proposal.reason.strip(),
            provenance=dict(proposal.provenance),
            added_work_unit_ids=sorted(
                unit.work_unit_id
                for unit in context["added_units"].values()
            ),
            added_edge_ids=sorted(
                edge.edge_id
                for edge in context["added_edges"].values()
            ),
            removed_work_unit_ids=sorted(
                context["removed_unit_ids"]
            ),
            removed_edge_ids=sorted(context["removed_edge_ids"]),
            edges_requiring_demand_recompile=sorted(
                edge.edge_id
                for edge in context["added_edges"].values()
            ),
            authority_sha256="pending",
        )
        authority_sha256 = (
            self.revision_authority.compute_revision_sha256(revision)
        )
        revision.authority_sha256 = authority_sha256
        revision.revision_id = f"semantic_graph_revision_{authority_sha256[:24]}"
        return revision

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
        ready = [
            node_id
            for node_id, degree in indegree.items()
            if degree == 0
        ]
        visited = 0
        while ready:
            node_id = ready.pop()
            visited += 1
            for target in adjacency[node_id]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
        return visited == len(node_ids)

    def _blocked(self, reason: str) -> SemanticGraphRevisionApplication:
        return SemanticGraphRevisionApplication(
            status="blocked",
            reason_codes=[reason],
        )

    def _insufficient(
        self,
        reason: str,
    ) -> SemanticGraphRevisionApplication:
        return SemanticGraphRevisionApplication(
            status="insufficient_contract_evidence",
            reason_codes=[reason],
        )
