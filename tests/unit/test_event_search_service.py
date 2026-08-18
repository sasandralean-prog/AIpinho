from aipinho.schemas.events.event_search_request import EventSearchRequest
from aipinho.services.events.event_search_service import EventSearchService
def test_event_search_returns_result_object():
    r=EventSearchService().search(EventSearchRequest(query="none",limit=5)); assert r.total>=0
