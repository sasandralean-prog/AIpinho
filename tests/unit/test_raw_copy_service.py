from aipinho.services.events.event_core import EventRawPayloadStore
from aipinho.services.interaction.raw_copy_service import RawCopyService
def test_raw_copy_returns_sanitized_payload():
    ref=EventRawPayloadStore().store("sprint36_raw_copy",{"auth":"sk-abcdefghijklmnop"}); r=RawCopyService().copy(ref); assert r.allowed and "sk-" not in r.text
