from __future__ import annotations

from pathlib import Path

import pytest

from aipinho.schemas.agents.tool_gateway import ToolDefinition, WorkspaceResolution
from aipinho.services.agents.multi_agent_policy_audit_store import MultiAgentPolicyAuditStore
from aipinho.services.agents.multi_agent_policy_kernel_service import MultiAgentPolicyKernelService


def _service(tmp_path: Path) -> MultiAgentPolicyKernelService:
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


def _tool(name: str, capability: str, *, write: bool = False, shell: bool = False, risk: str = "low") -> ToolDefinition:
    return ToolDefinition(tool_name=name, display_name=name, description=name, capability=capability, risk_level=risk, requires_workspace=True, can_modify_filesystem=write, can_run_shell=shell)


def _workspace(role: str) -> WorkspaceResolution:
    return WorkspaceResolution(workspace_id=f"ws_{role}", workspace_role=role, allowed=True, reason_code="workspace_allowed")


@pytest.mark.multi_agent
@pytest.mark.freedom
def test_safe_read_validation_and_report_generation_autoapprove(tmp_path):
    service = _service(tmp_path)
    read = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("read_file", "read_workspace"), workspace=_workspace("source_readonly"), input_summary_sanitized="read")
    validate = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("validate", "validation", risk="low"), workspace=_workspace("target_mutable"), input_summary_sanitized="validate")
    report = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=_tool("create_artifact", "artifact", risk="low"), workspace=_workspace("target_mutable"), input_summary_sanitized="report")

    assert read.decision == "auto_approve"
    assert validate.decision in {"allow", "auto_approve"}
    assert report.decision in {"allow", "auto_approve"}


@pytest.mark.multi_agent
@pytest.mark.freedom
def test_governed_autorun_and_power_user_allow_safe_target_mutations(tmp_path):
    service = _service(tmp_path)
    tool = _tool("create_file", "workspace_write", write=True, risk="medium")
    governed = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=tool, workspace=_workspace("target_mutable"), input_summary_sanitized="create file", execution_mode="governed_autorun")
    power = service.evaluate_tool_invocation(agent_id="codex", session_id="s", run_id="r", tool=tool, workspace=_workspace("target_mutable"), input_summary_sanitized="modify file", execution_mode="power_user")
    safe_chat = service.evaluate_tool_invocation(agent_id="aipinho", session_id="s", run_id="r", tool=tool, workspace=_workspace("target_mutable"), input_summary_sanitized="create file", execution_mode="safe_chat")

    assert governed.decision == "auto_approve"
    assert power.decision == "auto_approve"
    assert safe_chat.decision == "deny"
    assert safe_chat.reason_code
    assert safe_chat.human_reason


@pytest.mark.multi_agent
@pytest.mark.freedom
def test_safe_shell_categories_are_allowed_without_manual_bureaucracy(tmp_path):
    service = _service(tmp_path)
    shell = _tool("run_shell", "shell", shell=True, risk="medium")

    for category in ["readonly_shell", "test_shell", "build_shell", "package_shell"]:
        decision = service.evaluate_tool_invocation(agent_id="codex", session_id="s", run_id="r", tool=shell, workspace=_workspace("target_mutable"), input_summary_sanitized=category, shell_category=category, execution_mode="power_user")
        assert decision.decision == "auto_approve"
