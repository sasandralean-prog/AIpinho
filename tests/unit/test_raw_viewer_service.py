from aipinho.services.events.event_core import EventRawPayloadStore
from aipinho.services.interaction.raw_viewer_service import RawViewerService
def test_raw_viewer_redacts_token_and_hides_by_default():
    ref=EventRawPayloadStore().store("sprint36_raw_viewer",{"auth":"Bearer abcdefghijklmnop"}); r=RawViewerService().viewer(ref); assert r.hidden_by_default; assert "Bearer abc" not in r.sanitized_text
