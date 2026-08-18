from fastapi.testclient import TestClient
from aipinho.main import app
from aipinho.schemas.context.contracts import ContextBundle,ContextScope
from aipinho.services.context.context_core import ContextBundleRepository
client=TestClient(app)

def test_dry_run_api_no_execution():
    b=ContextBundle(request_id='r',purpose='skill_execution_future',scope=ContextScope()); ContextBundleRepository().save(b); body=client.post('/api/v1/skills/dry-run',json={'skill_id':'aipinho.context_explainer','context_bundle_id':b.bundle_id}).json(); assert body['status']=='completed'; assert body['safe_to_execute'] is False
