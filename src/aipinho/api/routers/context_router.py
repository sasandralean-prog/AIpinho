from __future__ import annotations
from fastapi import APIRouter, HTTPException
from aipinho.schemas.context.contracts import ContextBuildRequest, ContextCacheInvalidation, ContextPreviewRequest, ContextRequest
from aipinho.services.context.context_core import ChunkClassifier, ChunkDedupeService, ContextBundleRepository, ContextCacheService, ContextExplainService, ContextKernelService, ContextTraceService, SmartChunker
router=APIRouter(prefix='/api/v1/context',tags=['context-kernel'])
@router.get('/status')
def context_status(): return ContextKernelService().status()
@router.post('/preview')
def context_preview(request:ContextPreviewRequest): return ContextKernelService().preview(request)
@router.post('/build')
def context_build(request:ContextBuildRequest):
    result=ContextKernelService().build(request)
    return {'status':result.status,'bundle':result.bundle.model_dump()}
@router.post('/admit')
def context_admit(request:ContextRequest): return ContextKernelService().admit(request)
@router.get('/bundles/{bundle_id}')
def context_bundle(bundle_id:str):
    bundle=ContextBundleRepository().get(bundle_id)
    if bundle is None: raise HTTPException(status_code=404,detail='context_bundle_not_found')
    return {'status':'ok','bundle':bundle.model_dump()}
@router.get('/bundles/{bundle_id}/explain')
def context_explain(bundle_id:str):
    try: return {'status':'ok','explain':ContextExplainService().explain(bundle_id).model_dump()}
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail='context_bundle_not_found') from exc
@router.get('/bundles/{bundle_id}/trace')
def context_trace(bundle_id:str):
    bundle=ContextBundleRepository().get(bundle_id)
    if bundle is None or not bundle.trace_id: raise HTTPException(status_code=404,detail='context_trace_not_found')
    trace=ContextTraceService().get(bundle.trace_id)
    return {'status':'ok','trace':trace.model_dump() if trace else None}
@router.post('/injection-plan')
def context_injection_plan(payload:dict[str,object]):
    bundle_id=str(payload.get('bundle_id') or '')
    role_id=payload.get('role_id')
    try: return {'status':'ok','plan':ContextKernelService().injection_plan(bundle_id, str(role_id) if role_id else None).model_dump()}
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail='context_bundle_not_found') from exc
@router.post('/chunks/classify')
def context_chunks_classify(payload:dict[str,object]):
    chunks=SmartChunker().chunk(str(payload.get('text','')))
    return {'status':'ok','chunks':[c.model_dump() for c in chunks],'classifications':[ChunkClassifier().classify(c).model_dump() for c in chunks]}
@router.post('/chunks/dedupe')
def context_chunks_dedupe(request:ContextRequest):
    kept,dups=ChunkDedupeService().dedupe(request.candidates)
    return {'status':'ok','kept':[c.model_dump() for c in kept],'duplicates':dups}
@router.post('/explain-source')
def context_explain_source(payload:dict[str,object]): return {'status':'ok','source_ref':payload.get('source_ref'),'owner':'context_kernel','freshness_checked':True}
