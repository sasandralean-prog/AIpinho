from __future__ import annotations

from typing import Any

from aipinho.services.semantics.semantic_nway_topology_service import (
    SemanticNWayTopologyService,
)


class SemanticNWayProjectionService:
    """Projects immutable graph/edge semantics into N-way neighborhood and join views."""

    def __init__(
        self,
        *,
        topology: SemanticNWayTopologyService | None = None,
    ) -> None:
        self.topology = topology or SemanticNWayTopologyService()

    def project(self, *, run: Any) -> dict[str, Any]:
        plan = getattr(run, "plan", None)
        graph = getattr(plan, "semantic_execution_graph", None)
        if plan is None:
            return {
                "status": "not_available",
                "reason_codes": ["SEMANTIC_NWAY_PLAN_REQUIRED"],
            }
        if graph is None:
            return {
                "status": "not_available",
                "reason_codes": ["SEMANTIC_NWAY_GRAPH_REQUIRED"],
            }

        plan.semantic_topology_neighborhoods = []
        plan.semantic_join_evaluations = []
        neighborhood_failures: list[dict[str, Any]] = []
        join_failures: list[dict[str, Any]] = []

        for unit in graph.work_units:
            neighborhood = self.topology.neighborhood(
                run=run,
                work_unit_id=unit.work_unit_id,
            )
            if neighborhood is None:
                neighborhood_failures.append(
                    {
                        "work_unit_id": unit.work_unit_id,
                        "reason_codes": [
                            "SEMANTIC_NWAY_NEIGHBORHOOD_UNAVAILABLE"
                        ],
                    }
                )
                continue
            plan.semantic_topology_neighborhoods.append(neighborhood)

        incoming_by_consumer: dict[str, int] = {}
        for edge in graph.edges:
            incoming_by_consumer[edge.consumer_work_unit_id] = (
                incoming_by_consumer.get(edge.consumer_work_unit_id, 0) + 1
            )

        for consumer_work_unit_id in sorted(incoming_by_consumer):
            result = self.topology.evaluate_join(
                run=run,
                consumer_work_unit_id=consumer_work_unit_id,
            )
            if result.status == "evaluated" and result.join is not None:
                plan.semantic_join_evaluations.append(result.join)
                continue
            if result.status == "not_applicable":
                continue
            join_failures.append(
                {
                    "consumer_work_unit_id": consumer_work_unit_id,
                    "reason_codes": list(result.reason_codes),
                }
            )

        neighborhood_bindings = [
            {
                "neighborhood_id": item.neighborhood_id,
                "work_unit_id": item.work_unit_id,
                "authority_sha256": item.authority_sha256,
                "fan_in_count": item.fan_in_count,
                "fan_out_count": item.fan_out_count,
            }
            for item in plan.semantic_topology_neighborhoods
        ]
        join_bindings = [
            {
                "join_id": item.join_id,
                "consumer_work_unit_id": item.consumer_work_unit_id,
                "authority_sha256": item.authority_sha256,
                "decision": item.decision,
                "required_edge_ids": list(item.required_edge_ids),
            }
            for item in plan.semantic_join_evaluations
        ]
        plan.metadata["semantic_topology_neighborhood_bindings"] = (
            neighborhood_bindings
        )
        plan.metadata["semantic_join_evaluation_bindings"] = join_bindings
        plan.metadata["semantic_nway_projection"] = {
            "neighborhoods_projected": len(
                plan.semantic_topology_neighborhoods
            ),
            "joins_evaluated": len(plan.semantic_join_evaluations),
            "neighborhood_failures": neighborhood_failures,
            "join_failures": join_failures,
        }
        return {
            "status": "projected",
            "neighborhoods_projected": len(
                plan.semantic_topology_neighborhoods
            ),
            "joins_evaluated": len(plan.semantic_join_evaluations),
            "neighborhood_failures": neighborhood_failures,
            "join_failures": join_failures,
        }
