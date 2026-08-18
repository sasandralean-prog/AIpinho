from aipinho.services.context.context_core import ChunkClassifier, SmartChunker

def test_chunk_classifier_types_and_unknown():
    cls=ChunkClassifier(); assert cls.classify(SmartChunker().chunk('schema_version: 1 policy')[0]).chunk_type=='config_policy'
    assert cls.classify(SmartChunker().chunk('')[0]).chunk_type=='unknown'
