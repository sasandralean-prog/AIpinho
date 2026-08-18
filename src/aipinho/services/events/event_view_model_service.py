from __future__ import annotations
from aipinho.schemas.events.event_view_model import EventViewModel
from aipinho.services.events.event_core import EventPublicPayloadBuilder, EventStoreRepository
from aipinho.services.events.event_render_policy_service import EventRenderPolicyService
class EventViewModelService:
    def view_model(self,event_id:str)->EventViewModel:
        event=EventStoreRepository().get(event_id)
        if event is None: raise FileNotFoundError(event_id)
        payload=EventPublicPayloadBuilder().build(event).model_dump(); decision=EventRenderPolicyService().decide(payload); title=str(payload.get("event_type") or event_id)
        if decision.render_status=="blocked": title="Evento bloqueado/degradado"
        return EventViewModel(event_id=event_id,title=title,summary=str(payload.get("human_summary") or "Sem resumo humano."),severity=str(payload.get("severity") or "info"),status=str(payload.get("status") or "created"),visibility=str(payload.get("visibility") or "public"),copy_available=str(payload.get("copy_policy") or "")!="copy_blocked",raw_available=bool(payload.get("raw_available")),render_decision=decision.model_dump())
