from fastapi.testclient import TestClient
from aipinho.app_factory import create_app

def test_context_cache_api_status_invalidate_entries():
    c=TestClient(create_app())
    assert c.get('/api/v1/context/cache/status').status_code==200
    assert c.post('/api/v1/context/cache/invalidate',json={'reason':'test'}).status_code==200
    assert c.get('/api/v1/context/cache/entries').status_code==200
