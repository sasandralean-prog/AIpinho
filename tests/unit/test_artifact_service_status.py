from aipinho.services.artifacts.artifact_service_status import ArtifactServiceStatus
from aipinho.services.artifacts.artifact_link_policy_service import ArtifactLinkPolicyService


def test_artifact_service_status_and_direct_workspace_blocked():
    status = ArtifactServiceStatus().status()
    policy = ArtifactLinkPolicyService().policy()
    assert status["port"] == 9098
    assert status["direct_workspace_serve_enabled"] is False
    assert policy["direct_workspace_serve_enabled"] is False
