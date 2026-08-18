from __future__ import annotations

from pathlib import Path

from aipinho.schemas.agents.tool_gateway import ToolDefinition, WorkspaceResolution
from aipinho.services.agents.multi_agent_policy_kernel_service import MultiAgentPolicyKernelService
from aipinho.services.agents.multi_agent_policy_audit_store import MultiAgentPolicyAuditStore


def _configs(tmp_path: Path) -> Path:
    root = tmp_path / "config"
    (root / "agents").mkdir(parents=True)
    (root / "policies").mkdir(parents=True)
    (root / "agents" / "agent_policy_profiles.yaml").write_text(Path("config/agents/agent_policy_profiles.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (root / "policies" / "multi_agent_autoapproval_policy.yaml").write_text(Path("config/policies/multi_agent_autoapproval_policy.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (root / "policies" / "block_reason_codes.yaml").write_text(Path("config/policies/block_reason_codes.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    return root


def _service(tmp_path: Path) -> MultiAgentPolicyKernelService:
    root = _configs(tmp_path)
    return MultiAgentPolicyKernelService(
        root=root,
        profile_path=root / "agents" / "agent_policy_profiles.yaml",
        autoapproval_path=root / "policies" / "multi_agent_autoapproval_policy.yaml",
        block_reasons_path=root / "policies" / "block_reason_codes.yaml",
        store=MultiAgentPolicyAuditStore(tmp_path / "policy_store"),
    )


def _tool(name: str, capability: str, *, write: bool = False, shell: bool = False, risk: str = "low") -> ToolDefinition:
    return ToolDefinition(
        tool_name=name,
        display_name=name,
        description=name,
        capability=capability,
        risk_level=risk,
        requires_workspace=write or shell or capability in {"read_workspace", "workspace_write"},
        can_modify_filesystem=write,
        can_run_shell=shell,
    )


def _workspace(role: str, allowed: bool = True) -> WorkspaceResolution:
    return WorkspaceResolution(workspace_id=f"ws_{role}", workspace_role=role, allowed=allowed, reason_code="workspace_allowed", evidence_refs=[f"workspace:{role}"])


def test_policy_decision_modes_allow_deny_require_and_autoapprove(tmp_path):
    service = _service(tmp_path)
    read = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("read_file", "read_workspace"), workspace=_workspace("source_readonly"), input_summary_sanitized="read")
    write_assisted = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("create_file", "workspace_write", write=True, risk="medium"), workspace=_workspace("target_mutable"), input_summary_sanitized="write", execution_mode="assisted_execution")
    write_source = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("create_file", "workspace_write", write=True, risk="medium"), workspace=_workspace("source_readonly"), input_summary_sanitized="write")

    assert read.decision == "auto_approve"
    assert read.auto_approval_id
    assert write_assisted.decision == "require_approval"
    assert write_assisted.safe_actions
    assert write_source.decision == "deny"
    assert write_source.reason_code == "source_readonly_write_denied"


def test_execution_modes_safe_chat_governed_and_power_user(tmp_path):
    service = _service(tmp_path)
    write_tool = _tool("create_file", "workspace_write", write=True, risk="medium")
    safe = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=write_tool, workspace=_workspace("target_mutable"), input_summary_sanitized="write", execution_mode="safe_chat")
    governed = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=write_tool, workspace=_workspace("target_mutable"), input_summary_sanitized="write", execution_mode="governed_autorun")
    power = service.evaluate_tool_invocation(agent_id="codex", session_id="s", run_id="r", tool=write_tool, workspace=_workspace("target_mutable"), input_summary_sanitized="write", execution_mode="power_user")

    assert safe.decision == "deny"
    assert governed.decision == "auto_approve"
    assert power.decision == "auto_approve"


def test_shell_policy_blocks_dangerous_and_autoapproves_safe(tmp_path):
    service = _service(tmp_path)
    shell = _tool("run_shell", "shell", shell=True, risk="medium")
    readonly = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=shell, workspace=_workspace("target_mutable"), input_summary_sanitized="echo ok", shell_category="readonly_shell")
    build = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=shell, workspace=_workspace("target_mutable"), input_summary_sanitized="build", shell_category="build_shell")
    destructive = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=shell, workspace=_workspace("target_mutable"), input_summary_sanitized="delete", shell_category="destructive_shell")
    network = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=shell, workspace=_workspace("target_mutable"), input_summary_sanitized="curl", shell_category="network_shell")

    assert readonly.decision == "auto_approve"
    assert build.decision == "auto_approve"
    assert destructive.decision == "deny"
    assert destructive.reason_code == "destructive_shell_blocked"
    assert network.decision == "deny"
    assert network.reason_code == "network_shell_blocked"


def test_secret_risk_blocks_and_audits_decision(tmp_path):
    service = _service(tmp_path)
    decision = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("read_file", "read_workspace"), workspace=_workspace("source_readonly"), input_summary_sanitized="Authorization: Bearer SECRET_VALUE_12345")

    assert decision.decision == "deny"
    assert decision.reason_code == "secret_access_blocked"
    assert service.store.get_policy_decision(decision.policy_decision_id) is not None


def test_kernel_status_and_block_reason_catalog(tmp_path):
    service = _service(tmp_path)
    status = service.status()
    reasons = service._block_reasons()

    assert status.default_execution_mode == "governed_autorun"
    assert status.power_user_enabled is True
    assert "source_readonly_write_denied" in reasons
