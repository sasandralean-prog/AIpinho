from fastapi.testclient import TestClient
from aipinho.app_factory import create_app
from aipinho.services.context.context_core import ContextKernelService, RAGContextAdapter, ArtifactContextAdapter, VisionOCRContextAdapter
from tests.unit.context_test_helpers import request, candidate

def test_context_kernel_v1_governed_flow_cases():
    c=TestClient(create_app()); assert c.get('/api/v1/context/status').json()['context_admission_owner']=='context_kernel'
    svc=ContextKernelService()
    assert svc.preview(request(candidates=[candidate(layer='chat_session',source_type='chat_message',source_id='m',cited=False)]))['status']=='ok'
    assert svc.preview(request(purpose='ghost'))['status']=='blocked'
    assert 'rejected' in {d['status'] for d in svc.admit(request(candidates=[candidate(cited=False)]))['decisions']}
    assert 'admitted' in {d['status'] for d in svc.admit(request(candidates=[RAGContextAdapter().candidate('r','rag',True)]))['decisions']}
    assert 'rejected' in {d['status'] for d in svc.admit(request(candidates=[RAGContextAdapter().candidate('r2','rag',False)]))['decisions']}
    direct=ArtifactContextAdapter().candidate('a','artifact',path='C:\\Users\\x.txt')
    assert 'rejected' in {d['status'] for d in svc.admit(request(purpose='artifact_generation',candidates=[direct]))['decisions']}
    raw=candidate(layer='chat_session',source_type='raw_prompt',source_id='raw',cited=False)
    assert 'rejected' in {d['status'] for d in svc.admit(request(candidates=[raw]))['decisions']}
    vision=VisionOCRContextAdapter().visual('v','image')
    assert 'admitted' in {d['status'] for d in svc.admit(request(purpose='vision_analysis',candidates=[vision]))['decisions']}
    built=svc.build(request(candidates=[RAGContextAdapter().candidate('r3','rag',True)]))
    assert built.bundle.citation_map and built.bundle.safe_for_prompt and built.bundle.rejected_items==[]
    plan=svc.injection_plan(built.bundle.bundle_id,'coder'); assert plan.citation_map==built.bundle.citation_map
