from __future__ import annotations

import subprocess
from pathlib import Path

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.agents.multi_agent_policy_audit_store import MultiAgentPolicyAuditStore
from aipinho.services.agents.multi_agent_policy_kernel_service import MultiAgentPolicyKernelService


class FakeShellRunner:
    def run(self, argv, cwd, timeout):
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


def _gateway(tmp_path: Path):
    target = tmp_path / "target"
    source = tmp_path / "source"
    target.mkdir()
    source.mkdir()
    config = tmp_path / "config"
    (config / "agents").mkdir(parents=True)
    (config / "policies").mkdir(parents=True)
    for rel in [
        "config/agents/tool_gateway_registry.yaml",
        "config/agents/agent_policy_profiles.yaml",
        "config/policies/multi_agent_autoapproval_policy.yaml",
        "config/policies/block_reason_codes.yaml",
    ]:
        dest = config / rel.removeprefix("config/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(Path(rel).read_text(encoding="utf-8"), encoding="utf-8")
    (config / "agents" / "tool_gateway_workspaces.yaml").write_text(
        f"""
version: 1
workspaces:
  - workspace_id: target
    root: {target}
    role: target_mutable
    enabled: true
  - workspace_id: source
    root: {source}
    role: source_readonly
    enabled: true
""",
        encoding="utf-8",
    )
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))
    policy_kernel = MultiAgentPolicyKernelService(
        root=config,
        profile_path=config / "agents" / "agent_policy_profiles.yaml",
        autoapproval_path=config / "policies" / "multi_agent_autoapproval_policy.yaml",
        block_reasons_path=config / "policies" / "block_reason_codes.yaml",
        store=MultiAgentPolicyAuditStore(tmp_path / "policy_store"),
    )
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config / "agents" / "tool_gateway_registry.yaml", root=config),
        resolver=AgentToolWorkspaceResolver(config / "agents" / "tool_gateway_workspaces.yaml", root=config),
        policy=AgentToolPolicyDecisionService(root=config, kernel=policy_kernel),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        shell_runner=FakeShellRunner(),
    )
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Policy integration"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="policy_gateway", status="running"))
    return gateway, kernel, policy_kernel, session, run, target


def test_gateway_uses_policy_kernel_autoapproval_events(tmp_path):
    gateway, kernel, policy_kernel, _, run, target = _gateway(tmp_path)
    result = gateway.invoke("aipinho", run.run_id, "create_file", ToolInvocationCreateRequest(workspace_id="target", input={"relative_path": "ok.txt", "content": "ok"}))

    assert result.status == "succeeded"
    assert result.policy_decision is not None
    assert result.policy_decision.execution_mode == "governed_autorun"
    assert result.policy_decision.decision == "auto_approve"
    assert policy_kernel.store.get_policy_decision(result.policy_decision.policy_decision_id) is not None
    assert (target / "ok.txt").exists()
    events = {event.event_type for event in kernel.list_run_events(run.run_id, include_hidden=True)}
    assert {"policy_check_started", "policy_decision_auto_approve", "auto_approval_granted", "tool_succeeded"} <= events


def test_gateway_policy_denies_source_readonly_with_safe_alternative(tmp_path):
    gateway, kernel, _, _, run, _ = _gateway(tmp_path)
    result = gateway.invoke("aipinho", run.run_id, "create_file", ToolInvocationCreateRequest(workspace_id="source", input={"relative_path": "blocked.txt", "content": "no"}))

    assert result.status == "blocked"
    assert result.tool_invocation.block_reason_code == "source_readonly_write_denied"
    assert result.policy_decision is not None
    assert result.policy_decision.safe_alternative
    events = {event.event_type for event in kernel.list_run_events(run.run_id, include_hidden=True)}
    assert {"policy_decision_deny", "operation_blocked", "safe_alternative_available"} <= events


def test_assisted_execution_requires_safe_action_for_write(tmp_path):
    gateway, _, _, _, run, _ = _gateway(tmp_path)
    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "create_file",
        ToolInvocationCreateRequest(
            workspace_id="target",
            input={"relative_path": "needs_approval.txt", "content": "x"},
            metadata_sanitized={"execution_mode": "assisted_execution"},
        ),
    )

    assert result.status == "approval_required"
    assert result.policy_decision is not None
    assert result.policy_decision.safe_actions
    assert result.policy_decision.safe_actions[0]["side_effect"] == "filesystem_write"
