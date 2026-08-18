from __future__ import annotations
from aipinho.schemas.ux.ux_health import UXHealth
from aipinho.services.ux.ux_degraded_state_service import UXDegradedStateService
class UXHealthService:
    def health(self, service_states: dict[str,str]|None=None, last_snapshot: dict[str,object]|None=None) -> UXHealth:
        states=service_states or {}; degraded=UXDegradedStateService().consolidate(states); offline=bool(states.get("backend") in {"down","offline"})
        return UXHealth(state="healthy" if not degraded else ("offline" if offline else "degraded"),degraded_states=[i.model_dump() for i in degraded],offline=offline,last_successful_snapshot=last_snapshot,warnings=[i.human_message for i in degraded])
