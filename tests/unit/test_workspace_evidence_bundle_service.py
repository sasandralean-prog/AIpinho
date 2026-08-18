from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

from aipinho.schemas.artifacts.workspace_evidence_bundle import WorkspaceEvidenceBundleRequest
from aipinho.schemas.roles.role_pass import RolePass
from aipinho.schemas.roles.role_pass_output import RolePassOutput
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.artifacts.workspace_evidence_bundle_service import WorkspaceEvidenceBundleService


class _ShellRunner:
    def run(self, argv, cwd, timeout):
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


class _Reporter:
    def run(self, role_input):
        role_pass = RolePass(pass_id=role_input.pass_id, role_id="reporter", required=True, status="completed")
        role_pass.output = RolePassOutput(
            role_id="reporter",
            status="completed",
            source="model_evaluated",
            content="# Evidence Bundle Summary\n\nFase 1: PASS\nFase 2: PASS\n",
        )
        return role_pass


def _bundle_service(tmp_path: Path, *, policy_root_name: str = "target", target_child_name: str | None = None):
    policy_root = tmp_path / policy_root_name
    target = policy_root / target_child_name if target_child_name else policy_root
    target.mkdir(parents=True)
    config_root = tmp_path / "config"
    (config_root / "agents").mkdir(parents=True)
    for name in ("tool_gateway_registry.yaml", "tool_gateway_policy.yaml"):
        (config_root / "agents" / name).write_text(Path("config/agents", name).read_text(encoding="utf-8"), encoding="utf-8")
    (config_root / "agents" / "tool_gateway_workspaces.yaml").write_text(
        f"version: 1\nworkspaces:\n  - workspace_id: target\n    root: {policy_root}\n    role: target_mutable\n    enabled: true\n",
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
    policy = {
        "workspace_evidence_bundle": {
            "enabled": True,
            "max_source_files": 20,
            "max_archive_files": 20,
            "max_archive_bytes": 1000000,
            "max_chars_per_file": 5000,
            "max_total_context_chars": 10000,
            "allowed_text_extensions": [".md", ".txt", ".json"],
            "ignored_directories": ["build"],
            "reporter": {"enabled": True, "allow_real_inference": False, "fallback_to_manifest": True},
        }
    }
    return WorkspaceEvidenceBundleService(kernel=kernel, gateway=gateway, resolver=resolver, reporter=_Reporter(), policy=policy), target


def test_bundle_service_writes_summary_and_validated_zip_through_gateway(tmp_path):
    service, target = _bundle_service(tmp_path)
    (target / "reports").mkdir()
    (target / "reports" / "analysis.md").write_text("validation passed", encoding="utf-8")
    (target / "README.md").write_text("project", encoding="utf-8")

    result = service.execute(WorkspaceEvidenceBundleRequest(
        session_id="chat_test",
        operation_id="operation_test",
        workspace_ref="target",
        prompt="Gere summary e bundle a partir da evidencia.",
        summary_relative_path="reports/summary.md",
        archive_relative_path="reports/bundle.zip",
        source_relative_paths=["reports/analysis.md", "README.md"],
        title="Evidence Bundle Summary",
    ))

    assert result.status == "completed"
    assert result.validation_status == "passed"
    assert result.run_id and result.summary_tool_invocation_id and result.archive_tool_invocation_id
    assert (target / "reports" / "summary.md").exists()
    assert result.artifact_id and result.download_endpoint
    with zipfile.ZipFile(target / "reports" / "bundle.zip", "r") as bundle:
        assert set(bundle.namelist()) == {"README.md", "reports/analysis.md", "reports/summary.md"}


def test_bundle_service_uses_resolved_child_path_inside_allowed_workspace_root(tmp_path):
    service, target = _bundle_service(tmp_path, policy_root_name="allowed", target_child_name="child_project")
    (target / "reports").mkdir()
    (target / "reports" / "analysis.md").write_text("validation passed", encoding="utf-8")
    (target / "README.md").write_text("project", encoding="utf-8")

    result = service.execute(WorkspaceEvidenceBundleRequest(
        session_id="chat_test",
        operation_id="operation_test",
        workspace_ref=str(target),
        prompt="Gere summary e bundle a partir da evidencia.",
        summary_relative_path="reports/summary.md",
        archive_relative_path="reports/bundle.zip",
        source_relative_paths=["reports/analysis.md", "README.md"],
        title="Evidence Bundle Summary",
    ))

    assert result.status == "completed"
    assert (target / "reports" / "summary.md").exists()
    assert (target / "reports" / "bundle.zip").exists()
    assert not (target.parent / "reports" / "bundle.zip").exists()
