from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.agents.memory import (
    MemoryCandidateCreateRequest,
    MemoryCandidateReviewRequest,
    MemoryContextLoadRequest,
    MemorySearchRequest,
    MemorySupersedeRequest,
    MemoryWriteRequest,
)
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.services.agents.agent_delegation_policy_service import AgentDelegationPolicyService
from aipinho.services.agents.agent_delegation_service import AgentDelegationService
from aipinho.services.agents.agent_delegation_store import AgentDelegationStore
from aipinho.services.agents.agent_memory_gateway_service import AgentMemoryGatewayService
from aipinho.services.agents.agent_memory_gateway_store import AgentMemoryGatewayStore
from aipinho.services.agents.agent_memory_policy_service import AgentMemoryPolicyService
from aipinho.services.agents.agent_profile_registry_service import AgentProfileRegistryService
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver


def _copy_configs(tmp_path: Path) -> Path:
    config = tmp_path / "config"
    for rel in [
        "config/agents/agent_registry.yaml",
        "config/agents/memory_gateway_policy.yaml",
        "config/agents/delegation_policy.yaml",
        "config/agents/tool_gateway_registry.yaml",
        "config/agents/tool_gateway_policy.yaml",
        "config/policies/multi_agent_autoapproval_policy.yaml",
        "config/policies/block_reason_codes.yaml",
    ]:
        dest = config / rel.removeprefix("config/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text((PROJECT_ROOT / rel).read_text(encoding="utf-8"), encoding="utf-8")
    return config


def _kernel(tmp_path: Path, config: Path) -> AgentSessionKernelService:
    return AgentSessionKernelService(
        profiles=AgentProfileRegistryService(config / "agents" / "agent_registry.yaml", root=config),
        store=AgentSessionStore(tmp_path / "agent_kernel"),
    )


def _memory_service(tmp_path: Path):
    config = _copy_configs(tmp_path)
    kernel = _kernel(tmp_path, config)
    service = AgentMemoryGatewayService(
        store=AgentMemoryGatewayStore(tmp_path / "memory_gateway"),
        policy=AgentMemoryPolicyService(config / "agents" / "memory_gateway_policy.yaml", root=config),
        kernel=kernel,
    )
    return service, kernel, config


def _run(kernel: AgentSessionKernelService, agent_id: str = "aipinho"):
    session = kernel.create_session(agent_id, AgentSessionCreateRequest(title=f"{agent_id} memory"))
    run = kernel.create_run(agent_id, session.session_id, AgentRunCreateRequest(operation_type="memory_test", status="running", workspace_id="workspace_a"))
    return session, run


def test_private_memory_is_agent_owned_and_cross_agent_write_is_blocked(tmp_path):
    service, _, _ = _memory_service(tmp_path)

    own = service.write_memory(
        MemoryWriteRequest(
            agent_id="codex",
            namespace="memory:codex",
            title="Fix pattern",
            content_sanitized="Use validated tool gateway traces for code execution lessons.",
            memory_type="fix_pattern",
            source_ref="report:unit",
            evidence_refs=["report:unit"],
        )
    )
    blocked = service.write_memory(
        MemoryWriteRequest(
            agent_id="gemini",
            namespace="memory:codex",
            title="Wrong owner",
            content_sanitized="This should not enter another agent private memory.",
            memory_type="policy_lesson",
            source_ref="report:unit",
            evidence_refs=["report:unit"],
        )
    )

    assert own.status == "written"
    assert own.memory is not None
    assert own.memory.agent_id == "codex"
    assert blocked.status == "blocked"
    assert blocked.policy.reason_code == "private_memory_cross_agent_denied"


def test_shared_memory_candidate_accept_creates_validated_record(tmp_path):
    service, _, _ = _memory_service(tmp_path)
    candidate = service.create_candidate(
        MemoryCandidateCreateRequest(
            proposed_by_agent_id="lucio",
            namespace="memory:shared",
            scope="shared",
            title="Reusable delegation lesson",
            content_sanitized="Delegations should carry sanitized evidence refs instead of raw logs.",
            memory_type="workflow_lesson",
            source_ref="report:sprint6",
            evidence_refs=["report:sprint6"],
            confidence="high",
            reason_to_remember="Reusable multi-agent workflow governance lesson.",
        )
    )

    result = service.accept_candidate(candidate.candidate_id, MemoryCandidateReviewRequest(agent_id="aipinho", reviewed_by="aipinho"))

    assert result.status == "written"
    assert result.memory is not None
    assert result.memory.namespace == "memory:shared"
    assert result.memory.validation_status == "validated"
    assert service.store.get_candidate(candidate.candidate_id).status == "accepted"


def test_secret_and_chain_of_thought_are_blocked_from_memory(tmp_path):
    service, _, _ = _memory_service(tmp_path)

    secret = service.write_memory(
        MemoryWriteRequest(
            agent_id="aipinho",
            namespace="memory:aipinho",
            title="Bad secret",
            content_sanitized="Bearer SECRET_VALUE_1234567890 should never persist.",
            memory_type="security_lesson",
            source_ref="test",
        )
    )
    raw_reasoning = service.write_memory(
        MemoryWriteRequest(
            agent_id="aipinho",
            namespace="memory:aipinho",
            title="Bad reasoning",
            content_sanitized="chain_of_thought: hidden reasoning is not a memory artifact.",
            memory_type="policy_lesson",
            source_ref="test",
        )
    )

    assert secret.status == "blocked"
    assert raw_reasoning.status == "blocked"
    assert secret.policy.reason_code == "memory_secret_blocked"
    assert raw_reasoning.policy.reason_code == "memory_chain_of_thought_blocked"


def test_memory_record_update_is_policy_checked_and_logged(tmp_path):
    service, _, _ = _memory_service(tmp_path)
    written = service.write_memory(
        MemoryWriteRequest(
            agent_id="aipinho",
            namespace="memory:aipinho",
            title="Safe lesson",
            content_sanitized="Use governed memory updates for reusable lessons.",
            memory_type="policy_lesson",
            source_ref="test",
        )
    )
    assert written.memory is not None

    updated, policy = service.update_record(
        written.memory.memory_id,
        {"title": "Updated lesson", "content_sanitized": "Updated safe content."},
        agent_id="aipinho",
    )

    assert updated.title == "Updated lesson"
    assert policy.decision == "allow"
    assert service.store.list_access(memory_id=written.memory.memory_id)[-1].access_type == "update"

    try:
        service.update_record(
            written.memory.memory_id,
            {"content_sanitized": "api_key=SECRET_VALUE_1234567890"},
            agent_id="aipinho",
        )
    except PermissionError as exc:
        assert str(exc) == "memory_secret_blocked"
    else:
        raise AssertionError("secret update should be blocked")


def test_search_context_and_supersede_update_agent_run_memory_refs(tmp_path):
    service, kernel, _ = _memory_service(tmp_path)
    _, run = _run(kernel, "aipinho")
    written = service.write_memory(
        MemoryWriteRequest(
            agent_id="aipinho",
            namespace="memory:aipinho",
            title="Intent routing lesson",
            content_sanitized="Simple conversation should not become a task when no side effect is requested.",
            memory_type="prompt_routing_lesson",
            source_ref="report:intent",
            evidence_refs=["report:intent"],
            run_id=run.run_id,
            session_id=run.session_id,
        )
    )
    assert written.memory is not None

    search = service.search(MemorySearchRequest(agent_id="aipinho", query="conversation task", run_id=run.run_id, session_id=run.session_id))
    context = service.load_context_for_run(MemoryContextLoadRequest(agent_id="aipinho", run_id=run.run_id))
    superseded = service.supersede(written.memory.memory_id, MemorySupersedeRequest(agent_id="aipinho", reason="superseded_by_newer_lesson"))
    updated_run = kernel.get_run(run.run_id)

    assert search.records
    assert context.memory_refs_used
    assert superseded.validation_status == "superseded"
    assert written.memory.memory_id in updated_run.memory_refs_written
    assert written.memory.memory_id in updated_run.memory_refs_used


def test_delegation_carries_memory_context_as_sanitized_trace(tmp_path):
    service, kernel, config = _memory_service(tmp_path)
    delegation = AgentDelegationService(
        kernel=kernel,
        store=AgentDelegationStore(tmp_path / "delegations"),
        policy=AgentDelegationPolicyService(config / "agents" / "delegation_policy.yaml", root=config),
    )
    _, parent = _run(kernel, "lucio")

    response = delegation.create_delegation(
        "lucio",
        parent.run_id,
        DelegationCreateRequest(
            target_agent_id="codex",
            user_goal="Review with memory context",
            requested_operation="technical_analysis",
            capabilities_requested=["read_workspace"],
            memory_refs=["memory_example"],
            memory_context_sanitized={"lesson": "Use sanitized context only."},
            risk_level="low",
        ),
    )

    assert response.status == "running"
    assert response.delegation.memory_refs == ["memory_example"]
    child = kernel.get_run(response.delegation.child_run_id)
    assert child is not None
    assert child.metadata_sanitized["memory_refs"] == ["memory_example"]
    events = {event.event_type for event in kernel.list_run_events(parent.run_id, include_hidden=True)}
    assert "memory_context_attached_to_delegation" in events


def test_tool_gateway_artifact_creates_memory_candidate_best_effort(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "gateway_memory"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy_kernel"))
    service, kernel, config = _memory_service(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    (config / "agents" / "tool_gateway_workspaces.yaml").write_text(
        f"""
version: 1
workspaces:
  - workspace_id: target
    root: {target}
    role: target_mutable
    enabled: true
""",
        encoding="utf-8",
    )
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config / "agents" / "tool_gateway_registry.yaml", root=config),
        resolver=AgentToolWorkspaceResolver(config / "agents" / "tool_gateway_workspaces.yaml", root=config),
        policy=AgentToolPolicyDecisionService(config / "agents" / "tool_gateway_policy.yaml", root=config),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway"),
    )
    _, run = _run(kernel, "aipinho")

    result = gateway.invoke("aipinho", run.run_id, "create_artifact", ToolInvocationCreateRequest(input={"filename": "lesson.txt", "content": "usable lesson"}))
    updated_run = kernel.get_run(run.run_id)

    assert result.status == "succeeded"
    assert updated_run.memory_candidates_created
    assert "memory_candidate_created" in {event.event_type for event in kernel.list_run_events(run.run_id, include_hidden=True)}

