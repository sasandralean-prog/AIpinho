from __future__ import annotations
from fastapi import APIRouter
from aipinho.services.context.context_core import ContextPurposePolicyService, ContextLayerResolver
router=APIRouter(prefix='/api/v1/context/debug',tags=['context-debug'])
@router.get('/purposes')
def debug_purposes(): return ContextPurposePolicyService().status()
@router.get('/layers')
def debug_layers(): return {'status':'ok','layers':ContextLayerResolver().layers()}
