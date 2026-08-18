from aipinho.services.rag.retrieval_sensitivity_filter import RetrievalSensitivityFilter
from tests.unit.retrieval_test_helpers import cited_hit


def test_retrieval_sensitivity_filter_blocks_secret_private_key_raw_log_and_binary():
    service = RetrievalSensitivityFilter()
    assert service.inspect_text("api_key=abcdef123456")["allowed"] is False
    assert service.inspect_text("-----BEGIN PRIVATE KEY-----")["allowed"] is False
    assert service.inspect_text("raw log traceback (most recent call last)")["allowed"] is False
    assert service.inspect_text("abc\x00def")["allowed"] is False
    assert service.filter_hits([cited_hit("password=abcdef123456")]) == []
