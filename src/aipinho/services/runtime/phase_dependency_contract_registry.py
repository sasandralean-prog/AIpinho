from __future__ import annotations

from collections.abc import Iterable

from aipinho.schemas.runtime.phase_dependency_evaluation import DownstreamPhaseRequirements


class PhaseDependencyContractRegistry:
    """Fixed system invariants that can only strengthen compiled demand.

    Dynamic per-task requirements come from the canonical plan compiler. The
    registry is intentionally empty by default and is never a task-level
    authority or a fallback for missing plan semantics.
    """

    def __init__(self, requirements: Iterable[DownstreamPhaseRequirements] | None = None) -> None:
        self._requirements = {
            (item.consumer_phase_id, item.operation_type): item.model_copy(deep=True)
            for item in (requirements or [])
        }

    def resolve(self, consumer_phase_id: str, operation_type: str) -> DownstreamPhaseRequirements | None:
        return self.resolve_invariants(consumer_phase_id, operation_type)

    def resolve_invariants(self, consumer_phase_id: str, operation_type: str) -> DownstreamPhaseRequirements | None:
        requirements = self._requirements.get((str(consumer_phase_id), str(operation_type)))
        if requirements is None:
            requirements = self._requirements.get(("*", str(operation_type)))
        return requirements.model_copy(deep=True) if requirements is not None else None

    def contracts(self) -> list[DownstreamPhaseRequirements]:
        return [item.model_copy(deep=True) for item in self._requirements.values()]
