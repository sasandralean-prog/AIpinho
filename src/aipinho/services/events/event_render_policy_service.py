from __future__ import annotations
from aipinho.schemas.events.event_render_decision import EventRenderDecision
from aipinho.services.events.event_core import EventContractRegistryService
class EventRenderPolicyService:
    def decide(self,event:dict[str,object])->EventRenderDecision:
        event_type=str(event.get("event_type") or ""); event_id=str(event.get("event_id") or "") or None; visibility=str(event.get("visibility") or "public"); reasons=[]
        if EventContractRegistryService().get(event_type) is None: reasons.append("unknown_event_contract")
        if visibility in {"hidden","internal"}: reasons.append(f"visibility_{visibility}_hidden_by_default")
        return EventRenderDecision(event_id=event_id,event_type=event_type,render_status="blocked" if reasons else "normal",reasons=reasons)
