from aipinho.schemas.context.contracts import ContextRequest, ContextCandidate, ContextAdmissionDecision, ContextBundle, ContextItem, ContextInjectionPlan, SmartChunk, ContextSourceRef

def test_context_contracts_construct():
    ref=ContextSourceRef(source_type='current_request',source_id='r')
    req=ContextRequest(purpose='user_response'); cand=ContextCandidate(layer='current_message',source_type='current_request',source_ref=ref,summary='s')
    dec=ContextAdmissionDecision(candidate_id=cand.candidate_id,status='admitted')
    item=ContextItem(layer='current_message',source_type='current_request',source_ref=ref,summary='s',content='c',content_hash='h')
    bundle=ContextBundle(request_id=req.request_id,purpose=req.purpose,scope=req.scope,items=[item],admission_decisions=[dec])
    plan=ContextInjectionPlan(bundle_id=bundle.bundle_id,purpose=req.purpose)
    chunk=SmartChunk(text='x')
    assert bundle.items and plan.bundle_id and chunk.chunk_id
