from __future__ import annotations
from fastapi import APIRouter
from aipinho.schemas.context.contracts import ContextCacheInvalidation
from aipinho.services.context.context_core import ContextCacheRepository, ContextCacheService
router=APIRouter(prefix='/api/v1/context/cache',tags=['context-cache'])
@router.get('/status')
def cache_status(): return ContextCacheService().status()
@router.post('/invalidate')
def cache_invalidate(request:ContextCacheInvalidation): return ContextCacheService().invalidate(request)
@router.get('/entries')
def cache_entries(): return {'status':'ok','entries':[e.model_dump() for e in ContextCacheRepository().list()]}
