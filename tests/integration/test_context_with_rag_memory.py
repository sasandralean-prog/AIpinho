from aipinho.services.context.context_core import ContextKernelService, MemoryContextAdapter, RAGContextAdapter
from tests.unit.context_test_helpers import request

def statuses(req): return {d['status'] for d in ContextKernelService().admit(req)['decisions']}
def test_rag_and_memory_admission_rules():
    assert 'admitted' in statuses(request(candidates=[RAGContextAdapter().candidate('r','cited',True)]))
    assert 'rejected' in statuses(request(candidates=[RAGContextAdapter().candidate('r2','uncited',False)]))
    assert 'admitted' in statuses(request(candidates=[MemoryContextAdapter().candidate('m','approved')]))
    assert 'rejected' in statuses(request(candidates=[MemoryContextAdapter().candidate('m2','expired',freshness='expired')]))
    assert 'rejected' in statuses(request(candidates=[MemoryContextAdapter().candidate('m3','superseded',freshness='superseded')]))
