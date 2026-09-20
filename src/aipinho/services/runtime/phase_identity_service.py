from __future__ import annotations

from typing import Any, Mapping


class PhaseIdentityService:
    """Canonical resolver for structured runtime phase identity.

    Free-form prompt text is never inspected here. Aliases are accepted only at
    structured ingress; consumers should prefer the materialized TaskRun field.
    """

    PHASE_KEYS = ("current_phase", "phase_id", "mission_phase", "phase")

    def from_mapping(self, values: Mapping[str, Any] | None) -> str | None:
        if not isinstance(values, Mapping):
            return None
        for key in self.PHASE_KEYS:
            phase = self._clean(values.get(key))
            if phase:
                return phase
        return None

    def from_run(self, run: Any) -> str | None:
        materialized = self._clean(getattr(run, "current_phase", None))
        if materialized:
            return materialized
        for source_name in ("intent_map", "bootstrap_context"):
            phase = self.from_mapping(getattr(run, source_name, None))
            if phase:
                return phase
        workflow = getattr(run, "workflow", None)
        return self._clean(getattr(workflow, "current_phase", None))

    @staticmethod
    def _clean(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
