from __future__ import annotations
from fastapi import APIRouter, HTTPException
from aipinho.schemas.events.event_filter import EventFilter
from aipinho.schemas.events.event_search_request import EventSearchRequest
from aipinho.services.events.event_filter_service import EventFilterService
from aipinho.services.events.event_search_service import EventSearchService
from aipinho.services.events.event_view_model_service import EventViewModelService
router=APIRouter(prefix="/api/v1/events",tags=["events"])
@router.get("/search")
def search_events(query:str="",limit:int=100)->dict[str,object]: return EventSearchService().search(EventSearchRequest(query=query,limit=limit)).model_dump()
@router.post("/filter")
def filter_events(event_filter:EventFilter)->dict[str,object]: return {"status":"ok","events":EventFilterService().filter(event_filter)}
@router.get("/{event_id}/view-model")
def event_view_model(event_id:str)->dict[str,object]:
    try: return EventViewModelService().view_model(event_id).model_dump()
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail="event_not_found") from exc
