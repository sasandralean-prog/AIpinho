from aipinho.services.rag.retrieval_source_policy_service import RetrievalSourcePolicyService
from tests.unit.retrieval_test_helpers import request


def test_source_policy_allows_registered_readonly_and_blocks_unknown_legacy_network():
    service = RetrievalSourcePolicyService()
    assert service.validate_source("project_reports", request()).allowed is True
    assert service.validate_source("unknown", request(sources=["unknown"])).allowed is False
    assert service.validate_source("legacy_vectorstore", request(sources=["legacy_vectorstore"])).allowed is False
    assert service.validate_source("web", request(sources=["web"])).allowed is False


def test_curated_memory_requires_explicit_request():
    service = RetrievalSourcePolicyService()
    assert service.validate_source("curated_memory", request(sources=["curated_memory"], explicit=False)).allowed is False
    assert service.validate_source("curated_memory", request(sources=["curated_memory"], explicit=True)).allowed is True
