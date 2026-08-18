from fastapi.testclient import TestClient
from aipinho.app_factory import create_app
from aipinho.services.events.event_core import EventRawPayloadStore
def test_raw_viewer_api_redacts():
    ref=EventRawPayloadStore().store("sprint36_api_raw",{"auth":"Bearer abcdefghijklmnop"}); c=TestClient(create_app()); r=c.get(f"/api/v1/raw/{ref}/viewer"); assert r.status_code==200 and "Bearer abc" not in r.text
