from aipinho.services.events.event_core import EventRawPayloadStore
from aipinho.services.interaction.raw_search_service import RawSearchService
def test_raw_search_finds_sanitized_term():
    ref=EventRawPayloadStore().store("sprint36_raw_search",{"message":"needle"}); r=RawSearchService().search(ref,"needle"); assert r.total>=1
