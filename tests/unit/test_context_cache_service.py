from aipinho.services.context.context_core import ContextCacheService, ContextKernelService, ContextCandidateCollector
from aipinho.schemas.context.contracts import ContextCacheInvalidation
from tests.unit.context_test_helpers import request, candidate

def test_cache_hit_and_invalidation():
    cache=ContextCacheService(); cache.invalidate(ContextCacheInvalidation(reason='test'))
    req=request(candidates=[candidate(source_id='cache')]); built=ContextKernelService().build(req)
    assert cache.get_bundle(req, ContextCandidateCollector().collect(req)) is not None
    assert cache.invalidate(ContextCacheInvalidation(reason='policy_change'))['invalidated'] is True
