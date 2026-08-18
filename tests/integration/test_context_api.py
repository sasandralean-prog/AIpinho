from fastapi.testclient import TestClient
from aipinho.app_factory import create_app

def test_context_api_status_preview_build_explain_plan():
    c=TestClient(create_app())
    assert c.get('/api/v1/context/status').status_code==200
    payload={'purpose':'user_response','current_message':'ola','candidates':[{'layer':'governed_rag','source_type':'rag_chunk','source_ref':{'source_type':'rag_chunk','source_id':'r1'},'summary':'rag','content':'rag','trust_level':'cited','citations':[{'source_ref':{'source_type':'rag_chunk','source_id':'r1'},'label':'rag'}]}]}
    assert c.post('/api/v1/context/preview',json=payload).status_code==200
    built=c.post('/api/v1/context/build',json=payload); assert built.status_code==200
    bundle_id=built.json()['bundle']['bundle_id']
    assert c.get(f'/api/v1/context/bundles/{bundle_id}').status_code==200
    assert c.get(f'/api/v1/context/bundles/{bundle_id}/explain').status_code==200
    assert c.post('/api/v1/context/injection-plan',json={'bundle_id':bundle_id,'role_id':'coder'}).status_code==200
