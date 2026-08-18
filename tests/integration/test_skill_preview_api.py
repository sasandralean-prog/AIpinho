from fastapi.testclient import TestClient
from aipinho.main import app
from aipinho.schemas.context.contracts import ContextBundle,ContextScope
from aipinho.services.context.context_core import ContextBundleRepository
client=TestClient(app)

def test_preview_api_no_side_effects():
    b=ContextBundle(request_id='r',purpose='skill_execution_future',scope=ContextScope()); ContextBundleRepository().save(b); body=client.post('/api/v1/skills/preview',json={'skill_id':'aipinho.context_explainer','context_bundle_id':b.bundle_id}).json(); assert body['status']=='preview'; assert body['side_effects_performed'] is False
