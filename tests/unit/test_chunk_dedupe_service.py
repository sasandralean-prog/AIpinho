from aipinho.services.context.context_core import ChunkDedupeService
from tests.unit.context_test_helpers import candidate

def test_chunk_dedupe_same_hash_source():
    kept,dup=ChunkDedupeService().dedupe([candidate(source_id='a'),candidate(source_id='a')])
    assert len(kept)==1 and dup
