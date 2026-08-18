from __future__ import annotations

import subprocess
from pathlib import Path

from aipinho.schemas.artifacts.workspace_static_reachability_report import WorkspaceStaticReachabilityReportRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.artifacts.workspace_static_reachability_report_service import WorkspaceStaticReachabilityReportService


class _ShellRunner:
    def run(self, argv, cwd, timeout):
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


def _service(tmp_path: Path):
    root = tmp_path / "allowed"
    child = root / "project"
    child.mkdir(parents=True)
    config_root = tmp_path / "config"
    (config_root / "agents").mkdir(parents=True)
    for name in ("tool_gateway_registry.yaml", "tool_gateway_policy.yaml"):
        (config_root / "agents" / name).write_text(Path("config/agents", name).read_text(encoding="utf-8"), encoding="utf-8")
    (config_root / "agents" / "tool_gateway_workspaces.yaml").write_text(
        f"version: 1\nworkspaces:\n  - workspace_id: target\n    root: {root}\n    role: target_mutable\n    enabled: true\n",
        encoding="utf-8",
    )
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel"))
    resolver = AgentToolWorkspaceResolver(config_root / "agents" / "tool_gateway_workspaces.yaml", root=config_root)
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config_root / "agents" / "tool_gateway_registry.yaml", root=config_root),
        resolver=resolver,
        policy=AgentToolPolicyDecisionService(config_root / "agents" / "tool_gateway_policy.yaml", root=config_root),
        store=AgentToolInvocationStore(tmp_path / "tools"),
        shell_runner=_ShellRunner(),
    )
    return WorkspaceStaticReachabilityReportService(kernel=kernel, gateway=gateway, resolver=resolver), child


def test_static_reachability_report_writes_governed_report_for_expected_text(tmp_path):
    service, target = _service(tmp_path)
    ui_file = target / "src" / "main" / "kotlin" / "App.kt"
    ui_file.parent.mkdir(parents=True)
    ui_file.write_text('Text("Forge local pronto")', encoding="utf-8")

    result = service.execute(WorkspaceStaticReachabilityReportRequest(
        session_id="chat_test",
        operation_id="operation_test",
        workspace_ref=str(target),
        prompt="Valide o texto esperado.",
        expected_text="Forge local pronto",
        report_relative_path="reports/visual_qa.md",
    ))

    assert result.status == "completed"
    assert result.validation_status == "passed"
    assert result.matched_files == ["src/main/kotlin/App.kt"]
    assert (target / "reports" / "visual_qa.md").exists()
    assert "render_qa_passed_with_warning" in (target / "reports" / "visual_qa.md").read_text(encoding="utf-8")
