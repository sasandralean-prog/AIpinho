from aipinho.services.context.context_core import SmartChunker

def test_smart_chunker_splits_text():
    chunks=SmartChunker().chunk('abc'*1000,max_chars=1000); assert len(chunks)==3; assert chunks[0].content_hash
