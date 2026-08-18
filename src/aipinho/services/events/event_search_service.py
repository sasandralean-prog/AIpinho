from __future__ import annotations
from aipinho.schemas.events.event_filter import EventFilter
from aipinho.schemas.events.event_search_request import EventSearchRequest
from aipinho.schemas.events.event_search_result import EventSearchResult
from aipinho.services.events.event_filter_service import EventFilterService
class EventSearchService:
    def search(self,request:EventSearchRequest)->EventSearchResult:
        filters=EventFilter(**request.filters) if request.filters else EventFilter(); events=EventFilterService().filter(filters,limit=request.limit); query=request.query.lower().strip()
        if query: events=[e for e in events if query in " ".join(str(e.get(k,"")) for k in ("event_type","source_service","human_summary","severity","status")).lower()]
        return EventSearchResult(query=request.query,total=len(events),events=events[:request.limit])
