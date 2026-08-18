from fastapi.testclient import TestClient
from aipinho.app_factory import create_app
def test_event_search_and_filter_api():
    c=TestClient(create_app()); assert c.get("/api/v1/events/search").status_code==200; assert c.post("/api/v1/events/filter",json={}).status_code==200
