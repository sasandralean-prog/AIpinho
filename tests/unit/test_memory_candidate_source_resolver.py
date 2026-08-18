from aipinho.schemas.memory.memory_candidate import MemoryCandidateSource
from aipinho.services.memory.memory_candidate_source_resolver import MemoryCandidateSourceResolver


def test_manual_source_is_trusted_when_allowed():
    source = MemoryCandidateSourceResolver().resolve(MemoryCandidateSource(source_type="manual_payload", source_id="x"))
    assert source.trusted is True
    assert source.source_ref == "x"


def test_invalid_source_is_not_trusted():
    source = MemoryCandidateSourceResolver().resolve(MemoryCandidateSource(source_type="raw_log", source_id="x"))
    assert source.trusted is False


def test_metadata_source_resolution():
    source = MemoryCandidateSourceResolver().resolve(None, metadata={"source_type": "user_instruction", "source_id": "chat1"})
    assert source.source_type == "user_instruction"
    assert source.trusted is True
