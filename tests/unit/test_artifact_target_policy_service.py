from aipinho.services.artifacts.artifact_target_policy_service import ArtifactTargetPolicyService


def test_artifact_target_policy_lists_allowed_and_blocked():
    policy = ArtifactTargetPolicyService()
    assert ".md" in policy.allowed_extensions()
    assert ".py" in policy.blocked_extensions()
    assert "reports" in policy.allowed_base_dirs()
    assert "src" in policy.blocked_base_dirs()
