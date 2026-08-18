from __future__ import annotations

import subprocess
import zipfile
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


class FakeShellRunner:
    def __init__(self) -> None:
        self.last_argv = None
        self.last_cwd = None

    def run(self, argv, cwd, timeout):
        self.last_argv = argv
        self.last_cwd = cwd
        if "--fail" in argv:
            return subprocess.CompletedProcess(argv, 2, stdout="", stderr="failed")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


def _write_config(tmp_path: Path, source: Path, target: Path, protected: Path):
    config_root = tmp_path / "config"
    (config_root / "agents").mkdir(parents=True)
    (config_root / "agents" / "tool_gateway_registry.yaml").write_text(
        (Path("config/agents/tool_gateway_registry.yaml").read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    (config_root / "agents" / "tool_gateway_policy.yaml").write_text(
        (Path("config/agents/tool_gateway_policy.yaml").read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    (config_root / "agents" / "tool_gateway_workspaces.yaml").write_text(
        f"""
version: 1
workspaces:
  - workspace_id: source
    root: {source}
    role: source_readonly
    enabled: true
  - workspace_id: target
    root: {target}
    role: target_mutable
    enabled: true
  - workspace_id: protected_child
    root: {protected}
    role: forbidden
    enabled: true
""",
        encoding="utf-8",
    )
    return config_root


def _service(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    protected = target / "secret"
    source.mkdir()
    target.mkdir()
    protected.mkdir()
    (source / "readme.txt").write_text("hello Bearer SECRET_VALUE_12345", encoding="utf-8")
    (target / "existing.txt").write_text("old", encoding="utf-8")
    config_root = _write_config(tmp_path, source, target, protected)
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config_root / "agents" / "tool_gateway_registry.yaml", root=config_root),
        resolver=AgentToolWorkspaceResolver(config_root / "agents" / "tool_gateway_workspaces.yaml", root=config_root),
        policy=AgentToolPolicyDecisionService(config_root / "agents" / "tool_gateway_policy.yaml", root=config_root),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        shell_runner=FakeShellRunner(),
    )
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Tools"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="tool_test", status="running", workspace_id="target"))
    return gateway, kernel, session, run, source, target, protected


def test_registry_lists_minimum_tools(tmp_path):
    gateway, *_ = _service(tmp_path)
    tools = gateway.list_tools()
    names = {tool.tool_name for tool in tools}
    assert {"list_dir", "read_file", "search_files", "create_file", "modify_file", "run_shell", "create_artifact", "download_artifact"} <= names
    assert all(tool.capability for tool in tools)
    assert all(tool.risk_level for tool in tools)


def test_read_file_is_sanitized_and_emits_events(tmp_path):
    gateway, kernel, session, run, *_ = _service(tmp_path)
    result = gateway.invoke("aipinho", run.run_id, "read_file", ToolInvocationCreateRequest(workspace_id="source", input={"relative_path": "readme.txt"}))

    assert result.status == "succeeded"
    assert "[REDACTED_SECRET]" in result.output["content_sanitized"]
    events = kernel.list_run_events(run.run_id, include_hidden=True)
    assert {"tool_invocation_created", "tool_started", "tool_succeeded"} <= {event.event_type for event in events}


def test_write_source_readonly_is_blocked_and_target_mutable_succeeds(tmp_path):
    gateway, _, _, run, _, target, _ = _service(tmp_path)

    blocked = gateway.invoke("aipinho", run.run_id, "create_file", ToolInvocationCreateRequest(workspace_id="source", input={"relative_path": "blocked.txt", "content": "no"}))
    created = gateway.invoke("aipinho", run.run_id, "create_file", ToolInvocationCreateRequest(workspace_id="target", input={"relative_path": "created.txt", "content": "yes"}))

    assert blocked.status == "blocked"
    assert blocked.tool_invocation.block_reason_code == "source_readonly_write_denied"
    assert created.status == "succeeded"
    assert (target / "created.txt").read_text(encoding="utf-8") == "yes"


def test_workspace_resolution_blocks_traversal_and_deny_override(tmp_path):
    gateway, _, _, run, *_ = _service(tmp_path)

    traversal = gateway.invoke("aipinho", run.run_id, "read_file", ToolInvocationCreateRequest(workspace_id="source", input={"relative_path": "../target/existing.txt"}))
    denied_child = gateway.invoke("aipinho", run.run_id, "create_file", ToolInvocationCreateRequest(workspace_id="target", input={"relative_path": "secret/file.txt", "content": "x"}))

    assert traversal.status == "blocked"
    assert traversal.tool_invocation.block_reason_code == "path_traversal_denied"
    assert denied_child.status == "blocked"
    assert denied_child.tool_invocation.block_reason_code == "workspace_forbidden"


def test_shell_safe_category_runs_and_dangerous_categories_block(tmp_path):
    gateway, kernel, _, run, *_ = _service(tmp_path)
    safe = gateway.invoke("aipinho", run.run_id, "run_shell", ToolInvocationCreateRequest(workspace_id="target", input={"argv": ["echo", "ok"], "shell_category": "readonly_shell"}))
    dangerous = gateway.invoke("aipinho", run.run_id, "run_shell", ToolInvocationCreateRequest(workspace_id="target", input={"argv": ["echo", "bad"], "shell_category": "destructive_shell"}))

    assert safe.status == "succeeded"
    assert safe.output["exit_code"] == 0
    assert dangerous.status == "blocked"
    assert dangerous.tool_invocation.block_reason_code == "destructive_shell_blocked"
    assert "shell_stdout" in {event.event_type for event in kernel.list_run_events(run.run_id, include_hidden=True)}


def test_shell_absolute_cwd_inside_workspace_is_allowed(tmp_path):
    gateway, _, _, run, _, target, _ = _service(tmp_path)
    child = target / "child"
    child.mkdir()

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "run_shell",
        ToolInvocationCreateRequest(
            workspace_id="target",
            input={"argv": ["echo", "ok"], "cwd": str(child), "shell_category": "readonly_shell"},
        ),
    )

    assert result.status == "succeeded"
    assert gateway.shell_runner.last_cwd == str(child.resolve())


def test_shell_relative_workspace_executable_is_resolved_before_runner(tmp_path):
    gateway, _, _, run, _, target, _ = _service(tmp_path)
    script = target / "probe.bat"
    script.write_text("@echo off\necho ok", encoding="utf-8")

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "run_shell",
        ToolInvocationCreateRequest(
            workspace_id="target",
            input={"command": r".\probe.bat --version", "shell_category": "readonly_shell"},
        ),
    )

    assert result.status == "succeeded"
    assert gateway.shell_runner.last_argv == [str(script.resolve()), "--version"]


def test_artifact_create_and_download_metadata_are_token_safe(tmp_path):
    gateway, _, _, run, *_ = _service(tmp_path)
    result = gateway.invoke("aipinho", run.run_id, "create_artifact", ToolInvocationCreateRequest(input={"filename": "answer.txt", "content": "4"}))

    assert result.status == "succeeded"
    artifact = result.artifacts[0]
    assert artifact.requires_token is True
    assert "token" not in artifact.download_endpoint.lower()
    stored, content = gateway.read_artifact_bytes(artifact.artifact_id)
    assert stored.filename == "answer.txt"
    assert content == b"4"


def test_file_write_validation_checks_expected_content_marker(tmp_path):
    gateway, _, _, run, _, target, _ = _service(tmp_path)

    passed = gateway.invoke(
        "aipinho",
        run.run_id,
        "create_file",
        ToolInvocationCreateRequest(workspace_id="target", input={"relative_path": "expected.txt", "content": "alpha marker", "expected_contains": "marker"}),
    )
    failed = gateway.invoke(
        "aipinho",
        run.run_id,
        "create_file",
        ToolInvocationCreateRequest(workspace_id="target", input={"relative_path": "missing.txt", "content": "alpha", "expected_contains": "marker"}),
    )

    assert passed.status == "succeeded"
    assert passed.validation_result is not None
    assert passed.validation_result.status == "passed"
    assert failed.status == "succeeded"
    assert failed.validation_result is not None
    assert failed.validation_result.status == "failed"
    assert (target / "expected.txt").exists()


def test_validation_tool_returns_validation_result(tmp_path):
    gateway, kernel, _, run, *_ = _service(tmp_path)
    result = gateway.invoke("aipinho", run.run_id, "validate", ToolInvocationCreateRequest(input={"name": "contract", "status": "passed"}))

    assert result.status == "succeeded"
    assert result.validation_result is not None
    assert result.validation_result.status == "passed"
    assert "tool_succeeded" in {event.event_type for event in kernel.list_run_events(run.run_id)}


def test_create_archive_stays_inside_workspace_and_registers_validated_artifact(tmp_path):
    gateway, _, _, run, _, target, _ = _service(tmp_path)
    (target / "reports").mkdir()
    (target / "reports" / "one.md").write_text("evidence one", encoding="utf-8")
    (target / "README.md").write_text("evidence two", encoding="utf-8")

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "create_archive",
        ToolInvocationCreateRequest(
            workspace_id="target",
            path_ref=str(target / "reports" / "bundle.zip"),
            input={"source_paths": ["reports/one.md", "README.md"], "overwrite": True},
            metadata_sanitized={"execution_mode": "governed_autorun"},
        ),
    )

    assert result.status == "succeeded"
    assert result.validation_result is not None
    assert result.validation_result.status == "passed"
    assert result.artifacts and result.artifacts[0].requires_token is True
    with zipfile.ZipFile(target / "reports" / "bundle.zip", "r") as bundle:
        assert set(bundle.namelist()) == {"README.md", "reports/one.md"}
