from __future__ import annotations
from aipinho.schemas.ux.ux_action_state import UXActionState
class UXActionStateService:
    def state(self, action_id: str, backend_confirmed: bool=False, blocked_reasons: list[str]|None=None) -> UXActionState:
        reasons=blocked_reasons or []
        if reasons: return UXActionState(action_id=action_id,state="blocked",blocked=True,human_message=", ".join(reasons))
        if backend_confirmed: return UXActionState(action_id=action_id,state="success",blocked=False,human_message="Acao confirmada pelo backend.")
        return UXActionState(action_id=action_id,state="pending",blocked=False,human_message="Aguardando confirmacao do backend.")
