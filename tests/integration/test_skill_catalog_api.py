from fastapi.testclient import TestClient
from aipinho.main import app
client=TestClient(app)

def test_catalog_and_detail_api():
    status=client.get('/api/v1/skills/status'); assert status.status_code==200; assert status.json()['real_execution_enabled'] is False
    catalog=client.get('/api/v1/skills/catalog'); assert catalog.json()['count']==74
    detail=client.get('/api/v1/skills/aipinho.context_explainer'); assert detail.status_code==200
