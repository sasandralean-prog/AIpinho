from __future__ import annotations
from aipinho.schemas.events.event_filter import EventFilter
from aipinho.services.events.event_core import EventPublicPayloadBuilder, EventStoreRepository
from aipinho.services.events.event_render_policy_service import EventRenderPolicyService
class EventFilterService:
    def filter(self,event_filter:EventFilter,limit:int=100)->list[dict[str,object]]:
        builder=EventPublicPayloadBuilder(); out=[]
        for event in EventStoreRepository().list(limit=limit):
            item=builder.build(event).model_dump(); decision=EventRenderPolicyService().decide(item)
            if decision.render_status=="blocked" and not (event_filter.include_hidden or event_filter.include_internal): continue
            if event_filter.event_types and item.get("event_type") not in event_filter.event_types: continue
            if event_filter.source_services and item.get("source_service") not in event_filter.source_services: continue
            if event_filter.severities and item.get("severity") not in event_filter.severities: continue
            if event_filter.statuses and item.get("status") not in event_filter.statuses: continue
            payload=item.get("payload") if isinstance(item.get("payload"),dict) else {}
            if event_filter.task_id and payload.get("task_id")!=event_filter.task_id: continue
            if event_filter.session_id and payload.get("session_id")!=event_filter.session_id: continue
            if event_filter.trace_id and payload.get("trace_id")!=event_filter.trace_id: continue
            out.append(item)
        return out
