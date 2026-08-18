from fastapi.testclient import TestClient
from aipinho.main import app
from aipinho.schemas.context.contracts import ContextBundle,ContextScope
from aipinho.services.context.context_core import ContextBundleRepository
client=TestClient(app)

def test_governed_skill_flow_route_preview_dry_run_trace():
    route=client.post('/api/v1/skills/route',json={'category':'context','purpose':'explain context'}).json(); assert route['execution_started'] is False
    b=ContextBundle(request_id='e2e',purpose='skill_execution_future',scope=ContextScope()); ContextBundleRepository().save(b)
    preview=client.post('/api/v1/skills/preview',json={'skill_id':'aipinho.context_explainer','context_bundle_id':b.bundle_id}).json(); assert preview['status']=='preview'
    dry=client.post('/api/v1/skills/dry-run',json={'skill_id':'aipinho.context_explainer','context_bundle_id':b.bundle_id}).json(); assert dry['status']=='completed'; assert dry['side_effects_performed'] is False
    trace=client.get('/api/v1/skills/traces/'+dry['trace_id']); assert trace.status_code==200
