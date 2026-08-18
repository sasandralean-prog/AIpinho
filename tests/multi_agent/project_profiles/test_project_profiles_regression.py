from __future__ import annotations

from pathlib import Path

import pytest

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.projects import ProjectProfileCreateRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.projects import ProjectProfileRegistryService
from tests.multi_agent.fakes.agent_fakes import FakeShellRunner
from tests.multi_agent.fixtures.workspace_factory import create_regression_workspaces, write_gateway_config


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "project_profiles"


@pytest.mark.multi_agent
@pytest.mark.project_profiles
def test_project_profile_context_flows_to_run_tool_event_artifact_and_memory_scope(tmp_path):
    profile_registry = ProjectProfileRegistryService(root=tmp_path / "profiles_root")
    candidate = profile_registry.detect(FIXTURES / "python_project")
    profile = profile_registry.create(ProjectProfileCreateRequest(profile=candidate["proposed_profile"]))
    selected_workspace = profile.workspace_profiles[0]
    selected_validation = profile.validation_profiles[0]
    selected_command = profile.command_profiles[0]

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

    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Profiled run", project_profile_id=profile.project_id))
    run = kernel.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(
            operation_type="profiled_artifact",
            status="running",
            workspace_id="target",
            project_profile_id=profile.project_id,
            workspace_profile_id=selected_workspace.workspace_id,
            validation_profile_id=selected_validation.validation_profile_id,
            command_profile_ids=[selected_command.command_id],
        ),
    )

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "create_artifact",
        ToolInvocationCreateRequest(
            project_profile_id=profile.project_id,
            workspace_profile_id=selected_workspace.workspace_id,
            validation_profile_id=selected_validation.validation_profile_id,
            command_profile_id=selected_command.command_id,
            input={"filename": "profile-report.txt", "content": "profile context"},
        ),
    )

    assert result.status == "succeeded"
    assert result.tool_invocation.project_profile_id == profile.project_id
    assert result.artifacts[0].project_profile_id == profile.project_id
    events = kernel.list_run_events(run.run_id, include_hidden=True)
    assert any(event.payload_sanitized.get("project_profile_id") == profile.project_id for event in events)
    assert any(f"project:{profile.project_id}" in event.evidence_refs for event in events)
