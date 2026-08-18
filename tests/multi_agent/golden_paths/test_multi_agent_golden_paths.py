from __future__ import annotations

import pytest

from aipinho.schemas.agents.contracts import (
    AgentEventCreateRequest,
    AgentMessageCreateRequest,
    AgentRunCreateRequest,
    AgentSessionCreateRequest,
    AgentRunUpdateRequest,
)
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.services.agents.agent_delegation_service import AgentDelegationService
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from tests.multi_agent.fakes.agent_fakes import FakeCodexAdapter, FakeGeminiClient, FakeShellRunner
from tests.multi_agent.fixtures.workspace_factory import create_regression_workspaces, write_gateway_config


def _kernel(tmp_path):
    return AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))


def _gateway(tmp_path):
    workspaces = create_regression_workspaces(tmp_path)
    config_root = write_gateway_config(tmp_path, workspaces)
    kernel = _kernel(tmp_path)
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config_root / "agents" / "tool_gateway_registry.yaml", root=config_root),
        resolver=AgentToolWorkspaceResolver(config_root / "agents" / "tool_gateway_workspaces.yaml", root=config_root),
        policy=AgentToolPolicyDecisionService(config_root / "agents" / "tool_gateway_policy.yaml", root=config_root),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        shell_runner=FakeShellRunner(),
    )
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Regression"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="regression", status="running", workspace_id="target"))
    return gateway, kernel, session, run, workspaces


@pytest.mark.multi_agent
@pytest.mark.golden_path
def test_aipinho_simple_chat_keeps_session_message_and_final_answer(tmp_path):
    kernel = _kernel(tmp_path)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Simple chat"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="simple_chat", status="running"))
    user = kernel.add_message("aipinho", session.session_id, AgentMessageCreateRequest(role="user", content_sanitized="Quanto e dois mais dois?"))
    final = kernel.add_message("aipinho", session.session_id, AgentMessageCreateRequest(role="assistant", message_kind="final_answer", content_sanitized="4", run_id=run.run_id))
    kernel.add_event(run.run_id, AgentEventCreateRequest(event_type="final_answer_created", status="completed", human_message="Resposta final entregue.", evidence_refs=[f"message:{final.message_id}"]))
    kernel.update_run(run.run_id, AgentRunUpdateRequest(status="completed", final_message_id=final.message_id))

    messages = kernel.list_messages("aipinho", session.session_id)
    state = kernel.session_state("aipinho", session.session_id)

    assert [message.role for message in messages] == ["user", "assistant"]
    assert user.session_id == final.session_id
    assert state.latest_status == "completed"
    assert state.raw_available is False


@pytest.mark.multi_agent
@pytest.mark.golden_path
def test_tool_gateway_supports_read_write_artifact_validation_and_shell_paths(tmp_path):
    gateway, kernel, _, run, workspaces = _gateway(tmp_path)

    read = gateway.invoke("aipinho", run.run_id, "read_file", ToolInvocationCreateRequest(workspace_id="source", input={"relative_path": "README.md"}))
    write = gateway.invoke("aipinho", run.run_id, "create_file", ToolInvocationCreateRequest(workspace_id="target", input={"relative_path": "created.txt", "content": "ok"}))
    shell = gateway.invoke("aipinho", run.run_id, "run_shell", ToolInvocationCreateRequest(workspace_id="target", input={"argv": ["echo", "ok"], "shell_category": "test_shell"}))
    artifact = gateway.invoke("aipinho", run.run_id, "create_artifact", ToolInvocationCreateRequest(input={"filename": "report.txt", "content": "safe"}))
    validation = gateway.invoke("aipinho", run.run_id, "validate", ToolInvocationCreateRequest(input={"name": "smoke", "status": "passed"}))

    assert read.status == "succeeded"
    assert "[REDACTED_SECRET]" in read.output["content_sanitized"]
    assert write.status == "succeeded"
    assert (workspaces.target_mutable / "created.txt").read_text(encoding="utf-8") == "ok"
    assert shell.status == "succeeded"
    assert artifact.artifacts[0].artifact_id
    assert artifact.artifacts[0].requires_token is True
    assert "token" not in artifact.artifacts[0].download_endpoint.lower()
    assert validation.validation_result.status == "passed"
    assert {"tool_invocation_created", "tool_succeeded"} <= {event.event_type for event in kernel.list_run_events(run.run_id, include_hidden=True)}


@pytest.mark.multi_agent
@pytest.mark.golden_path
def test_delegation_creates_child_run_and_preserves_parent_evidence(tmp_path):
    kernel = _kernel(tmp_path)
    service = AgentDelegationService(kernel=kernel)
    parent_session = kernel.create_session("lucio", AgentSessionCreateRequest(title="Lucio"))
    parent_run = kernel.create_run("lucio", parent_session.session_id, AgentRunCreateRequest(operation_type="strategic_route", status="running", workspace_id="target"))

    response = service.create_delegation(
        "lucio",
        parent_run.run_id,
        DelegationCreateRequest(
            target_agent_id="codex",
            user_goal="Executar revisao tecnica segura com evidencia.",
            requested_operation="technical_execution",
            operation_type="code_review",
            workspace_id="target",
            capabilities_requested=["read_workspace"],
            expected_outputs=["diagnostic_report"],
            risk_level="low",
            execution_mode="governed_autorun",
        ),
    )

    assert response.status == "running"
    assert response.delegation.child_run_id
    assert response.result is not None
    assert response.result.evidence_refs
    assert kernel.get_run(response.delegation.child_run_id).parent_run_id == parent_run.run_id


@pytest.mark.multi_agent
@pytest.mark.golden_path
def test_fake_cloud_agents_are_explicit_and_do_not_use_real_provider():
    codex = FakeCodexAdapter().respond("revise")
    gemini = FakeGeminiClient().generate("explique")

    assert codex.provider == "fake_provider"
    assert gemini.provider == "fake_provider"
    assert codex.raw_hidden_by_default is True
    assert gemini.structured_actions == []
