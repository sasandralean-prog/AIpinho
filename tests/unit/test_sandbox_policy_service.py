from aipinho.services.security.sandbox_policy_service import SandboxPolicyService


def test_sandbox_policy_allows_workspace_bound_reads_in_governed_mode():
    status = SandboxPolicyService().status()
    assert status["mode"] == "governed_controlled"
    assert status["require_workspace"] is True
    assert status["workspace_bound_read"] is True
    assert SandboxPolicyService().allows_workspace_bound_read() is True
