from fastapi.testclient import TestClient
from aipinho.main import app
client=TestClient(app)

def test_route_selects_context_explainer_and_does_not_execute():
    body=client.post('/api/v1/skills/route',json={'category':'context','purpose':'explain context'}).json(); assert body['candidates'][0]['skill_id']=='aipinho.context_explainer'; assert body['execution_started'] is False
