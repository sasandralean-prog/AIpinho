from aipinho.services.rag.vector.role_rag_policy_service import RoleRAGPolicyService


def test_role_rag_policy_allows_only_declared_namespaces():
    service = RoleRAGPolicyService()

    assert service.can_access("coder", "coder_rag") is True
    assert service.can_access("coder", "global_ecosystem") is True
    assert service.can_access("coder", "code_reviewer_rag") is False
    assert service.status()["cross_role_namespace_access_enabled"] is False
