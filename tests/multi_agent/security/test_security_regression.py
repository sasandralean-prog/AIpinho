from __future__ import annotations

from pathlib import Path

import pytest

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest, ToolDefinition, WorkspaceResolution
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.agents.multi_agent_policy_audit_store import MultiAgentPolicyAuditStore
from aipinho.services.agents.multi_agent_policy_kernel_service import MultiAgentPolicyKernelService
from tests.multi_agent.fakes.agent_fakes import FakeShellRunner
from tests.multi_agent.fixtures.workspace_factory import create_regression_workspaces, write_gateway_config


def _gateway(tmp_path):
    workspaces = create_regression_workspaces(tmp_path)
    config_root = write_gateway_config(tmp_path, workspaces)
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config_root / "agents" / "tool_gateway_registry.yaml", root=config_root),
        resolver=AgentToolWorkspaceResolver(config_root / "agents" / "tool_gateway_workspaces.yaml", root=config_root),
        policy=AgentToolPolicyDecisionService(config_root / "agents" / "tool_gateway_policy.yaml", root=config_root),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        shell_runner=FakeShellRunner(),
    )
    session = kernel.create_session("codex", AgentSessionCreateRequest(title="Security"))
    run = kernel.create_run("codex", session.session_id, AgentRunCreateRequest(operation_type="security_regression", status="running", workspace_id="target"))
    return gateway, run, workspaces


def _policy(tmp_path):
    root = tmp_path / "config"
    (root / "agents").mkdir(parents=True)
    (root / "policies").mkdir()
    for src, dst in [
        ("config/agents/agent_policy_profiles.yaml", root / "agents" / "agent_policy_profiles.yaml"),
        ("config/policies/multi_agent_autoapproval_policy.yaml", root / "policies" / "multi_agent_autoapproval_policy.yaml"),
        ("config/policies/block_reason_codes.yaml", root / "policies" / "block_reason_codes.yaml"),
    ]:
        dst.write_text(Path(src).read_text(encoding="utf-8"), encoding="utf-8")
    return MultiAgentPolicyKernelService(
        root=root,
        profile_path=root / "agents" / "agent_policy_profiles.yaml",
        autoapproval_path=root / "policies" / "multi_agent_autoapproval_policy.yaml",
        block_reasons_path=root / "policies" / "block_reason_codes.yaml",
        store=MultiAgentPolicyAuditStore(tmp_path / "policy_store"),
    )


def _tool(name: str, capability: str, *, write: bool = False, shell: bool = False, risk: str = "medium") -> ToolDefinition:
    return ToolDefinition(
        tool_name=name,
        display_name=name,
        description=name,
        capability=capability,
        risk_level=risk,
        requires_workspace=write or shell,
        can_modify_filesystem=write,
        can_run_shell=shell,
    )


def _workspace(role: str) -> WorkspaceResolution:
    return WorkspaceResolution(workspace_id=f"ws_{role}", workspace_role=role, allowed=True, reason_code="workspace_allowed")


@pytest.mark.multi_agent
@pytest.mark.security
def test_source_readonly_forbidden_traversal_and_dangerous_shell_are_blocked(tmp_path):
    gateway, run, _ = _gateway(tmp_path)

    source_write = gateway.invoke("codex", run.run_id, "create_file", ToolInvocationCreateRequest(workspace_id="source", input={"relative_path": "blocked.txt", "content": "no"}))
    forbidden_write = gateway.invoke("codex", run.run_id, "create_file", ToolInvocationCreateRequest(workspace_id="forbidden", input={"relative_path": "blocked.txt", "content": "no"}))
    traversal = gateway.invoke("codex", run.run_id, "read_file", ToolInvocationCreateRequest(workspace_id="source", input={"relative_path": "../target/existing.txt"}))
    dangerous_shell = gateway.invoke("codex", run.run_id, "run_shell", ToolInvocationCreateRequest(workspace_id="target", input={"argv": ["echo", "bad"], "shell_category": "destructive_shell"}))

    assert source_write.status == "blocked"
    assert source_write.tool_invocation.block_reason_code == "source_readonly_write_denied"
    assert forbidden_write.status == "blocked"
    assert forbidden_write.tool_invocation.block_reason_code == "workspace_forbidden"
    assert traversal.status == "blocked"
    assert traversal.tool_invocation.block_reason_code == "path_traversal_denied"
    assert dangerous_shell.status == "blocked"
    assert dangerous_shell.tool_invocation.block_reason_code == "destructive_shell_blocked"


@pytest.mark.multi_agent
@pytest.mark.security
def test_policy_blocks_secret_network_and_git_write_risks(tmp_path):
    service = _policy(tmp_path)
    secret = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("read_file", "read_workspace", risk="low"), workspace=_workspace("source_readonly"), input_summary_sanitized="Bearer SECRET_VALUE_12345")
    network = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("run_shell", "shell", shell=True), workspace=_workspace("target_mutable"), input_summary_sanitized="curl http://example.invalid", shell_category="network_shell")
    git = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("run_shell", "shell", shell=True), workspace=_workspace("target_mutable"), input_summary_sanitized="git push", shell_category="git_write_shell")

    assert secret.decision == "deny"
    assert secret.reason_code == "secret_access_blocked"
    assert network.decision == "deny"
    assert git.decision == "deny"

