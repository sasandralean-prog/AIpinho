from aipinho.schemas.events.event_filter import EventFilter
from aipinho.services.events.event_filter_service import EventFilterService
def test_event_filter_returns_list():
    assert isinstance(EventFilterService().filter(EventFilter(),limit=5),list)
