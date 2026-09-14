from __future__ import annotations

from copy import deepcopy
from typing import Any

from aipinho.schemas.semantics.semantic_graph_revision import (
    SemanticGraphActivationResult,
    SemanticGraphHistorySnapshot,
    SemanticGraphRevisionApplication,
)
from aipinho.services.semantics.edge_semantic_demand_authority_service import (
    EdgeSemanticDemandAuthorityService,
)
from aipinho.services.semantics.edge_semantic_demand_compiler_service import (
    EdgeSemanticDemandCompilerService,
)
from aipinho.services.semantics.offer_demand_compatibility_authority_service import (
    OfferDemandCompatibilityAuthorityService,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.semantic_graph_revision_authority_service import (
    SemanticGraphRevisionAuthorityService,
)
from aipinho.services.semantics.semantic_nway_topology_authority_service import (
    SemanticNWayTopologyAuthorityService,
)
from aipinho.services.semantics.semantic_offer_authority_service import (
    SemanticOfferAuthorityService,
)


class SemanticGraphActivationService:
    """Activates a validated child graph while archiving parent-bound contracts."""

    VERSION = "semantic_graph_activation.v1"

    def __init__(
        self,
        *,
        graph_authority: SemanticExecutionGraphAuthorityService | None = None,
        revision_authority: SemanticGraphRevisionAuthorityService | None = None,
        demand_authority: EdgeSemanticDemandAuthorityService | None = None,
        offer_authority: SemanticOfferAuthorityService | None = None,
        compatibility_authority: OfferDemandCompatibilityAuthorityService
        | None = None,
        nway_authority: SemanticNWayTopologyAuthorityService | None = None,
        demand_compiler: EdgeSemanticDemandCompilerService | None = None,
    ) -> None:
        self.graph_authority = (
            graph_authority or SemanticExecutionGraphAuthorityService()
        )
        self.revision_authority = (
            revision_authority or SemanticGraphRevisionAuthorityService()
        )
        self.demand_authority = (
            demand_authority or EdgeSemanticDemandAuthorityService()
        )
        self.offer_authority = (
            offer_authority or SemanticOfferAuthorityService()
        )
        self.compatibility_authority = (
            compatibility_authority
            or OfferDemandCompatibilityAuthorityService()
        )
        self.nway_authority = (
            nway_authority or SemanticNWayTopologyAuthorityService()
        )
        self.demand_compiler = (
            demand_compiler or EdgeSemanticDemandCompilerService()
        )

    def activate(
        self,
        *,
        run: Any,
        application: SemanticGraphRevisionApplication,
    ) -> SemanticGraphActivationResult:
        if (
            application.status != "applied"
            or application.revision is None
            or application.child_graph is None
        ):
            return self._insufficient(
                "GRAPH_ACTIVATION_APPLIED_REVISION_REQUIRED"
            )

        plan = getattr(run, "plan", None)
        if plan is None:
            return self._insufficient("GRAPH_ACTIVATION_PLAN_REQUIRED")
        parent = getattr(plan, "semantic_execution_graph", None)
        if parent is None:
            return self._insufficient(
                "GRAPH_ACTIVATION_PARENT_GRAPH_REQUIRED"
            )
        revision = application.revision
        child = application.child_graph

        if not self.graph_authority.verify(parent):
            return self._insufficient(
                "GRAPH_ACTIVATION_PARENT_GRAPH_AUTHORITY_INVALID"
            )
        if not self.graph_authority.verify(child):
            return self._insufficient(
                "GRAPH_ACTIVATION_CHILD_GRAPH_AUTHORITY_INVALID"
            )
        if not self.revision_authority.verify(revision):
            return self._insufficient(
                "GRAPH_ACTIVATION_REVISION_AUTHORITY_INVALID"
            )
        if (
            revision.parent_graph_id != parent.semantic_graph_id
            or revision.parent_graph_authority_sha256
            != parent.authority_sha256
        ):
            return self._blocked("GRAPH_ACTIVATION_PARENT_BINDING_MISMATCH")
        if (
            revision.child_graph_id != child.semantic_graph_id
            or revision.child_graph_authority_sha256
            != child.authority_sha256
        ):
            return self._blocked("GRAPH_ACTIVATION_CHILD_BINDING_MISMATCH")

        chain_reason = self._validate_revision_chain(plan=plan, revision=revision)
        if chain_reason:
            return self._blocked(chain_reason)

        contract_reason = self._validate_current_contracts(
            plan=plan,
            parent=parent,
        )
        if contract_reason:
            return self._blocked(contract_reason)

        temp_run = deepcopy(run)
        temp_plan = temp_run.plan
        temp_plan.semantic_execution_graph = deepcopy(child)
        temp_plan.edge_semantic_demands = []
        temp_plan.semantic_offers = []
        temp_plan.offer_demand_compatibilities = []
        temp_plan.semantic_topology_neighborhoods = []
        temp_plan.semantic_join_evaluations = []

        recompiled_demands = []
        partial_demands = 0
        for edge in child.edges:
            compilation = self.demand_compiler.compile_for_edge(
                run=temp_run,
                edge_id=edge.edge_id,
            )
            if (
                compilation.status != "compiled"
                or compilation.demand is None
            ):
                reason = (
                    compilation.reason_codes[0]
                    if compilation.reason_codes
                    else "GRAPH_ACTIVATION_DEMAND_RECOMPILE_FAILED"
                )
                return self._blocked(reason)
            recompiled_demands.append(compilation.demand)
            if compilation.demand.status == "partial":
                partial_demands += 1

        snapshot = self._build_snapshot(
            plan=plan,
            parent=parent,
        )

        plan.semantic_graph_history.append(snapshot)
        plan.semantic_graph_revisions.append(deepcopy(revision))
        plan.semantic_execution_graph = deepcopy(child)
        plan.edge_semantic_demands = recompiled_demands
        plan.semantic_offers = []
        plan.offer_demand_compatibilities = []
        plan.semantic_topology_neighborhoods = []
        plan.semantic_join_evaluations = []
        plan.active_semantic_graph_revision_id = revision.revision_id
        plan.metadata["semantic_graph_revision_binding"] = {
            "active_revision_id": revision.revision_id,
            "revision_number": revision.revision_number,
            "active_graph_id": child.semantic_graph_id,
            "active_graph_authority_sha256": child.authority_sha256,
            "parent_graph_id": parent.semantic_graph_id,
            "parent_graph_authority_sha256": parent.authority_sha256,
            "history_snapshot_id": snapshot.snapshot_id,
        }
        plan.metadata["semantic_graph_history_count"] = len(
            plan.semantic_graph_history
        )
        plan.metadata["edge_semantic_demand_bindings"] = [
            {
                "demand_id": demand.demand_id,
                "edge_id": demand.edge_id,
                "authority_sha256": demand.authority_sha256,
                "status": demand.status,
            }
            for demand in recompiled_demands
        ]
        plan.metadata["semantic_offer_bindings"] = []
        plan.metadata["offer_demand_compatibility_bindings"] = []
        plan.metadata["semantic_topology_neighborhood_bindings"] = []
        plan.metadata["semantic_join_evaluation_bindings"] = []
        plan.metadata["semantic_result_projection"] = {
            "status": "invalidated_by_graph_revision",
            "active_graph_id": child.semantic_graph_id,
            "active_graph_authority_sha256": child.authority_sha256,
            "revision_id": revision.revision_id,
        }
        plan.metadata["semantic_nway_projection"] = {
            "status": "invalidated_by_graph_revision",
            "active_graph_id": child.semantic_graph_id,
            "active_graph_authority_sha256": child.authority_sha256,
            "revision_id": revision.revision_id,
        }

        return SemanticGraphActivationResult(
            status="activated",
            active_revision_id=revision.revision_id,
            active_graph_id=child.semantic_graph_id,
            active_graph_authority_sha256=child.authority_sha256,
            snapshot_id=snapshot.snapshot_id,
            demands_recompiled=len(recompiled_demands),
            partial_demands=partial_demands,
        )

    def _validate_revision_chain(
        self,
        *,
        plan: Any,
        revision: Any,
    ) -> str | None:
        revisions = list(
            getattr(plan, "semantic_graph_revisions", []) or []
        )
        active_revision_id = getattr(
            plan,
            "active_semantic_graph_revision_id",
            None,
        )
        if not revisions:
            if revision.revision_number != 1:
                return "GRAPH_ACTIVATION_REVISION_NUMBER_INVALID"
            if revision.parent_revision_id is not None:
                return "GRAPH_ACTIVATION_PARENT_REVISION_INVALID"
            if active_revision_id is not None:
                return "GRAPH_ACTIVATION_ACTIVE_REVISION_HISTORY_MISMATCH"
            return None

        last = revisions[-1]
        if active_revision_id != last.revision_id:
            return "GRAPH_ACTIVATION_ACTIVE_REVISION_HISTORY_MISMATCH"
        if revision.revision_number != last.revision_number + 1:
            return "GRAPH_ACTIVATION_REVISION_NUMBER_INVALID"
        if revision.parent_revision_id != last.revision_id:
            return "GRAPH_ACTIVATION_PARENT_REVISION_INVALID"
        if (
            revision.parent_graph_id != last.child_graph_id
            or revision.parent_graph_authority_sha256
            != last.child_graph_authority_sha256
        ):
            return "GRAPH_ACTIVATION_REVISION_PARENT_CHAIN_MISMATCH"
        return None

    def _validate_current_contracts(
        self,
        *,
        plan: Any,
        parent: Any,
    ) -> str | None:
        parent_id = parent.semantic_graph_id
        parent_sha = parent.authority_sha256

        for demand in list(
            getattr(plan, "edge_semantic_demands", []) or []
        ):
            if not self.demand_authority.verify(demand):
                return "GRAPH_ACTIVATION_DEMAND_AUTHORITY_INVALID"
            if (
                demand.semantic_graph_id != parent_id
                or demand.semantic_graph_authority_sha256 != parent_sha
            ):
                return "GRAPH_ACTIVATION_DEMAND_GRAPH_BINDING_MISMATCH"

        for offer in list(getattr(plan, "semantic_offers", []) or []):
            if not self.offer_authority.verify(offer):
                return "GRAPH_ACTIVATION_OFFER_AUTHORITY_INVALID"
            if (
                offer.semantic_graph_id != parent_id
                or offer.semantic_graph_authority_sha256 != parent_sha
            ):
                return "GRAPH_ACTIVATION_OFFER_GRAPH_BINDING_MISMATCH"

        for compatibility in list(
            getattr(plan, "offer_demand_compatibilities", []) or []
        ):
            if not self.compatibility_authority.verify(compatibility):
                return "GRAPH_ACTIVATION_COMPATIBILITY_AUTHORITY_INVALID"
            if (
                compatibility.semantic_graph_id != parent_id
                or compatibility.semantic_graph_authority_sha256
                != parent_sha
            ):
                return (
                    "GRAPH_ACTIVATION_COMPATIBILITY_GRAPH_BINDING_MISMATCH"
                )

        for neighborhood in list(
            getattr(plan, "semantic_topology_neighborhoods", []) or []
        ):
            if not self.nway_authority.verify_neighborhood(neighborhood):
                return "GRAPH_ACTIVATION_NEIGHBORHOOD_AUTHORITY_INVALID"
            if (
                neighborhood.semantic_graph_id != parent_id
                or neighborhood.semantic_graph_authority_sha256
                != parent_sha
            ):
                return (
                    "GRAPH_ACTIVATION_NEIGHBORHOOD_GRAPH_BINDING_MISMATCH"
                )

        for join in list(
            getattr(plan, "semantic_join_evaluations", []) or []
        ):
            if not self.nway_authority.verify_join(join):
                return "GRAPH_ACTIVATION_JOIN_AUTHORITY_INVALID"
            if (
                join.semantic_graph_id != parent_id
                or join.semantic_graph_authority_sha256 != parent_sha
            ):
                return "GRAPH_ACTIVATION_JOIN_GRAPH_BINDING_MISMATCH"
        return None

    def _build_snapshot(
        self,
        *,
        plan: Any,
        parent: Any,
    ) -> SemanticGraphHistorySnapshot:
        snapshot = SemanticGraphHistorySnapshot(
            snapshot_id="pending",
            revision_id=getattr(
                plan,
                "active_semantic_graph_revision_id",
                None,
            ),
            graph=deepcopy(parent),
            edge_semantic_demands=deepcopy(
                list(getattr(plan, "edge_semantic_demands", []) or [])
            ),
            semantic_offers=deepcopy(
                list(getattr(plan, "semantic_offers", []) or [])
            ),
            offer_demand_compatibilities=deepcopy(
                list(
                    getattr(
                        plan,
                        "offer_demand_compatibilities",
                        [],
                    )
                    or []
                )
            ),
            semantic_topology_neighborhoods=deepcopy(
                list(
                    getattr(
                        plan,
                        "semantic_topology_neighborhoods",
                        [],
                    )
                    or []
                )
            ),
            semantic_join_evaluations=deepcopy(
                list(
                    getattr(
                        plan,
                        "semantic_join_evaluations",
                        [],
                    )
                    or []
                )
            ),
            authority_sha256="pending",
        )
        sha = self.revision_authority.compute_snapshot_sha256(snapshot)
        snapshot.authority_sha256 = sha
        snapshot.snapshot_id = f"semantic_graph_history_{sha[:24]}"
        return snapshot

    def _blocked(self, reason: str) -> SemanticGraphActivationResult:
        return SemanticGraphActivationResult(
            status="blocked",
            reason_codes=[reason],
        )

    def _insufficient(
        self,
        reason: str,
    ) -> SemanticGraphActivationResult:
        return SemanticGraphActivationResult(
            status="insufficient_contract_evidence",
            reason_codes=[reason],
        )
