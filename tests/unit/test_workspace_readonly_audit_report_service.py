from __future__ import annotations

import subprocess
from pathlib import Path

from aipinho.schemas.artifacts.workspace_readonly_audit_report import WorkspaceReadonlyAuditReportRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.artifacts.workspace_readonly_audit_report_service import WorkspaceReadonlyAuditReportService


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
    return WorkspaceReadonlyAuditReportService(kernel=kernel, gateway=gateway, resolver=resolver), child


def test_readonly_audit_writes_governed_report_with_matches(tmp_path):
    service, target = _service(tmp_path)
    test_file = target / "tests" / "e2e" / "test_policy.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_gate():\n    assert 'real_inference' != 'stub.default'\n", encoding="utf-8")
    (target / "package.json").write_text(
        '{"name":"sample","scripts":{"build":"echo build"},"dependencies":{"react-native":"1.0.0"}}',
        encoding="utf-8",
    )

    result = service.execute(WorkspaceReadonlyAuditReportRequest(
        session_id="chat_test",
        operation_id="operation_test",
        workspace_ref=str(target),
        prompt="Audite testes e gere relatorio. Inclua:\n* stack detectada;\n* comandos candidatos;\n* criterio de sucesso;",
        report_relative_path="reports/audit.md",
        search_terms=["real_inference", "stub.default"],
    ))

    report = target / "reports" / "audit.md"
    assert result.status == "completed"
    assert result.validation_status == "passed"
    assert result.match_count == 1
    assert result.matched_files == ["tests/e2e/test_policy.py"]
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "workspace_readonly_audit" in text
    assert "## Sintese operacional" in text
    assert "Checklist solicitado" in text
    assert "build: `echo build`" in text
    assert "tests/e2e/test_policy.py" in text
