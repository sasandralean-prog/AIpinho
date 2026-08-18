from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry
from aipinho.services.rag.vector.vector_namespace_policy_service import VectorNamespacePolicyService


def test_vector_namespace_policy_blocks_unknown_disabled_and_disallowed_sources():
    registry = VectorIndexRegistry()
    policy = VectorNamespacePolicyService(registry)

    assert policy.validate(registry.get_namespace("coder_rag"), source_type="source_code_snapshots").allowed is True
    assert "source_not_allowed_for_namespace" in policy.validate(registry.get_namespace("coder_rag"), source_type="project_reports").blocked_reasons
    assert policy.validate(registry.get_namespace("vision_rag"), source_type="visual_evidence").allowed is True
    assert "source_not_allowed_for_namespace" in policy.validate(registry.get_namespace("vision_rag"), source_type="project_reports").blocked_reasons
    assert "unknown_namespace" in policy.validate(None).blocked_reasons
