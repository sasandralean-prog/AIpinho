from __future__ import annotations
from aipinho.schemas.context.contracts import ContextCandidate, ContextCitation, ContextRequest, ContextSourceRef, ChunkFreshness

def ref(source_type='rag_chunk', source_id='src1', path=None):
    return ContextSourceRef(source_type=source_type, source_id=source_id, path=path)
def citation(source_type='rag_chunk', source_id='src1'):
    return ContextCitation(source_ref=ref(source_type, source_id), label='test')
def candidate(layer='governed_rag', source_type='rag_chunk', source_id='src1', content='conteudo citado', cited=True, trust='cited', freshness='fresh', priority=5, path=None, metadata=None):
    return ContextCandidate(layer=layer, source_type=source_type, source_ref=ref(source_type, source_id, path), summary=content[:80], content=content, trust_level=trust, priority=priority, freshness=ChunkFreshness(status=freshness), citations=[citation(source_type, source_id)] if cited else [], metadata=metadata or {})
def request(purpose='user_response', candidates=None, current_message='ola', budget=None):
    return ContextRequest(purpose=purpose, current_message=current_message, candidates=candidates or [], max_budget_chars=budget)
