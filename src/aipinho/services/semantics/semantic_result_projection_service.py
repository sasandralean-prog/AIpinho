from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.semantics.observed_work_unit_outcome_projection_service import (
    ObservedWorkUnitOutcomeProjectionService,
)
from aipinho.services.semantics.offer_demand_compatibility_service import (
    OfferDemandCompatibilityService,
)
from aipinho.services.semantics.semantic_offer_compiler_service import (
    SemanticOfferCompilerService,
)


class SemanticResultProjectionService:
    """Projects terminal WorkUnit outcomes into Offers and edge compatibility.

    This is a projection boundary only. It never changes TaskRun terminal truth,
    never manufactures an Offer from a Demand, and never authorizes execution.
    """

    def __init__(
        self,
        *,
        outcomes: ObservedWorkUnitOutcomeProjectionService | None = None,
        offers: SemanticOfferCompilerService | None = None,
        compatibility: OfferDemandCompatibilityService | None = None,
    ) -> None:
        self.outcomes = (
            outcomes or ObservedWorkUnitOutcomeProjectionService()
        )
        self.offers = offers or SemanticOfferCompilerService()
        self.compatibility = (
            compatibility or OfferDemandCompatibilityService()
        )

    def project(
        self,
        *,
        run: Any,
        result: TaskRunResult,
    ) -> dict[str, Any]:
        plan = getattr(run, "plan", None)
        if plan is None:
            return {
                "status": "not_available",
                "reason_codes": ["SEMANTIC_RESULT_PLAN_REQUIRED"],
            }
        graph = getattr(plan, "semantic_execution_graph", None)
        if graph is None:
            return {
                "status": "not_available",
                "reason_codes": ["SEMANTIC_RESULT_GRAPH_REQUIRED"],
            }

        observed = self.outcomes.project(run=run, result=result)
        plan.semantic_offers = []
        plan.offer_demand_compatibilities = []

        offer_failures: list[dict[str, Any]] = []
        for outcome in observed:
            compiled = self.offers.compile_for_work_unit(
                run=run,
                observed=outcome,
            )
            if compiled.status == "compiled" and compiled.offer is not None:
                plan.semantic_offers.append(compiled.offer)
            else:
                offer_failures.append(
                    {
                        "producer_work_unit_id": outcome.producer_work_unit_id,
                        "status": compiled.status,
                        "reason_codes": list(compiled.reason_codes),
                    }
                )

        offers_by_unit = {
            offer.producer_work_unit_id: offer
            for offer in plan.semantic_offers
        }
        compatibility_failures: list[dict[str, Any]] = []
        for demand in list(getattr(plan, "edge_semantic_demands", []) or []):
            offer = offers_by_unit.get(demand.producer_work_unit_id)
            if offer is None:
                compatibility_failures.append(
                    {
                        "edge_id": demand.edge_id,
                        "producer_work_unit_id": demand.producer_work_unit_id,
                        "reason_codes": [
                            "OFFER_DEMAND_PRODUCER_OFFER_UNAVAILABLE"
                        ],
                    }
                )
                continue
            evaluation = self.compatibility.evaluate(
                run=run,
                offer=offer,
                demand=demand,
            )
            if (
                evaluation.status == "evaluated"
                and evaluation.compatibility is not None
            ):
                plan.offer_demand_compatibilities.append(
                    evaluation.compatibility
                )
            else:
                compatibility_failures.append(
                    {
                        "edge_id": demand.edge_id,
                        "producer_work_unit_id": demand.producer_work_unit_id,
                        "reason_codes": list(evaluation.reason_codes),
                    }
                )

        offer_bindings = [
            {
                "offer_id": offer.offer_id,
                "producer_work_unit_id": offer.producer_work_unit_id,
                "authority_sha256": offer.authority_sha256,
                "status": offer.status,
                "result_ref": offer.result_ref,
            }
            for offer in plan.semantic_offers
        ]
        compatibility_bindings = [
            {
                "compatibility_id": item.compatibility_id,
                "edge_id": item.edge_id,
                "offer_id": item.offer_id,
                "demand_id": item.demand_id,
                "authority_sha256": item.authority_sha256,
                "decision": item.decision,
            }
            for item in plan.offer_demand_compatibilities
        ]
        plan.metadata["semantic_offer_bindings"] = offer_bindings
        plan.metadata["offer_demand_compatibility_bindings"] = (
            compatibility_bindings
        )
        plan.metadata["semantic_result_projection"] = {
            "observed_work_unit_outcomes": len(observed),
            "offers_compiled": len(plan.semantic_offers),
            "compatibilities_evaluated": len(
                plan.offer_demand_compatibilities
            ),
            "offer_failures": offer_failures,
            "compatibility_failures": compatibility_failures,
        }

        return {
            "status": "projected",
            "observed_work_unit_outcomes": len(observed),
            "offers_compiled": len(plan.semantic_offers),
            "compatibilities_evaluated": len(
                plan.offer_demand_compatibilities
            ),
            "offer_failures": offer_failures,
            "compatibility_failures": compatibility_failures,
        }
