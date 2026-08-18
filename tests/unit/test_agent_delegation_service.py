
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.services.agents.agent_delegation_policy_service import AgentDelegationPolicyService
from aipinho.services.agents.agent_delegation_service import AgentDelegationService
from aipinho.services.agents.agent_delegation_store import AgentDelegationStore
from aipinho.services.agents.agent_profile_registry_service import AgentProfileRegistryService
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


def _copy_configs(tmp_path: Path) -> Path:
    config = tmp_path / "config"
    (config / "agents").mkdir(parents=True)
    (config / "policies").mkdir(parents=True)
    for rel in [
        "config/agents/agent_registry.yaml",
        "config/agents/delegation_policy.yaml",
        "config/agents/tool_gateway_registry.yaml",
        "config/agents/agent_policy_profiles.yaml",
        "config/policies/capability_registry.yaml",
        "config/policies/multi_agent_autoapproval_policy.yaml",
        "config/policies/block_reason_codes.yaml",
    ]:
        dest = config / rel.removeprefix("config/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(Path(rel).read_text(encoding="utf-8"), encoding="utf-8")
    return config


def _kernel(tmp_path: Path, config: Path) -> AgentSessionKernelService:
    return AgentSessionKernelService(
        profiles=AgentProfileRegistryService(config / "agents" / "agent_registry.yaml", root=config),
        store=AgentSessionStore(tmp_path / "agent_kernel"),
    )


def _service(tmp_path: Path):
    config = _copy_configs(tmp_path)
    kernel = _kernel(tmp_path, config)
    service = AgentDelegationService(
        kernel=kernel,
        store=AgentDelegationStore(tmp_path / "delegations"),
        policy=AgentDelegationPolicyService(config / "agents" / "delegation_policy.yaml", root=config),
    )
    return service, kernel, config


def _run(kernel: AgentSessionKernelService, agent_id: str = "lucio", *, parent_run_id: str | None = None):
    session = kernel.create_session(agent_id, AgentSessionCreateRequest(title=f"{agent_id} session"))
    run = kernel.create_run(
        agent_id,
        session.session_id,
        AgentRunCreateRequest(
            operation_type="parent",
            status="running",
            parent_run_id=parent_run_id,
            metadata_sanitized={"execution_mode": "governed_autorun"},
        ),
    )
    return session, run


def test_delegation_request_result_parent_child_and_timeline(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, parent_run = _run(kernel, "lucio")

    response = service.create_delegation(
        "lucio",
        parent_run.run_id,
        DelegationCreateRequest(
            target_agent_id="codex",
            user_goal="Analyze code safely",
            requested_operation="technical_analysis",
            capabilities_requested=["read_workspace"],
            expected_outputs=["summary"],
            risk_level="low",
        ),
    )

    assert response.status == "running"
    assert response.delegation.child_run_id
    assert response.policy_decision is not None
    assert response.policy_decision.decision == "auto_approve"
    assert response.result is not None
    assert response.result.evidence_refs
    child = kernel.get_run(response.delegation.child_run_id)
    assert child is not None
    assert child.parent_run_id == parent_run.run_id
    assert child.delegation_id == response.delegation.delegation_id
    assert kernel.get_run(parent_run.run_id).status == "delegation_running"
    parent_events = {event.event_type for event in kernel.list_run_events(parent_run.run_id, include_hidden=True)}
    child_events = {event.event_type for event in kernel.list_run_events(child.run_id, include_hidden=True)}
    assert {"delegation_created", "delegation_auto_approved", "delegation_child_run_started"} <= parent_events
    assert "delegation_child_run_started" in child_events


def test_policy_rejects_missing_capability_disabled_route_and_critical_risk(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, run = _run(kernel, "lucio")

    missing = service.create_delegation(
        "lucio",
        run.run_id,
        DelegationCreateRequest(target_agent_id="codex", user_goal="Visual task", requested_operation="image_generation", capabilities_requested=["vision"], risk_level="low"),
    )
    assert missing.status == "blocked"
    assert missing.result.reason_code == "target_agent_missing_capability"

    disabled = service.create_delegation(
        "lucio",
        run.run_id,
        DelegationCreateRequest(target_agent_id="gemini", user_goal="Disabled route", requested_operation="technical_analysis", risk_level="low"),
    )
    assert disabled.status == "blocked"
    assert disabled.result.reason_code == "parent_agent_not_allowed"

    critical = service.create_delegation(
        "lucio",
        run.run_id,
        DelegationCreateRequest(target_agent_id="codex", user_goal="Dangerous task", requested_operation="technical_analysis", capabilities_requested=["read_workspace"], risk_level="critical"),
    )
    assert critical.status == "blocked"
    assert critical.result.reason_code == "delegation_risk_too_high"


def test_delegation_normalizes_capability_aliases(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, run = _run(kernel, "gemini")

    response = service.create_delegation(
        "gemini",
        run.run_id,
        DelegationCreateRequest(
            target_agent_id="aipinho",
            user_goal="Generate a governed report artifact",
            requested_operation="artifact_request",
            capabilities_requested=["read_workspace", "create_artifact", "write_file", "delegate"],
            risk_level="low",
        ),
    )

    assert response.status == "running"
    assert response.policy_decision is not None
    assert response.policy_decision.decision == "auto_approve"
    assert response.delegation.child_run_id


def test_gemini_to_aipinho_capability_aliases_match(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, run = _run(kernel, "gemini")

    response = service.create_delegation(
        "gemini",
        run.run_id,
        DelegationCreateRequest(
            target_agent_id="aipinho",
            user_goal="Analyze, generate report artifact, build and test through governed phases.",
            requested_operation="delegated_governed_execution",
            capabilities_requested=["scan_workspace", "create_artifact", "run_shell_build", "run_tests", "validate_runtime"],
            risk_level="low",
        ),
    )

    assert response.status == "running"
    assert response.delegation.child_run_id
    assert response.policy_decision.metadata_sanitized["matched_aliases"]["scan_workspace"] == "read_workspace"
    assert response.policy_decision.metadata_sanitized["matched_aliases"]["create_artifact"] == "artifact_write"
    assert response.policy_decision.metadata_sanitized["matched_aliases"]["run_shell_build"] == "build"
    assert response.policy_decision.metadata_sanitized["matched_aliases"]["run_tests"] == "test"


def test_gemini_to_aipinho_can_start_readonly_phase_even_if_later_write_build_required(tmp_path):
    service, kernel, config = _service(tmp_path)
    policy_path = config / "agents" / "delegation_policy.yaml"
    text = policy_path.read_text(encoding="utf-8")
    text = text.replace(", build, test]", "]")
    text = text.replace(", build, test]\n    capabilities", "]\n    capabilities")
    policy_path.write_text(text, encoding="utf-8")
    registry_path = config / "agents" / "agent_registry.yaml"
    registry_text = registry_path.read_text(encoding="utf-8")
    registry_text = registry_text.replace("\n  - build\n  - test\n  - validation", "\n  - validation", 1)
    registry_path.write_text(registry_text, encoding="utf-8")
    kernel.profiles = AgentProfileRegistryService(registry_path, root=config)
    service.policy = AgentDelegationPolicyService(policy_path, root=config)
    _, run = _run(kernel, "gemini")

    response = service.create_delegation(
        "gemini",
        run.run_id,
        DelegationCreateRequest(
            target_agent_id="aipinho",
            user_goal="Start with read-only analysis and defer later build/test capabilities.",
            requested_operation="delegated_governed_execution",
            capabilities_requested=["read_workspace", "build", "test"],
            risk_level="low",
        ),
    )

    assert response.status == "running"
    assert response.delegation.child_run_id
    assert response.policy_decision.metadata_sanitized["deferred_capabilities"] == ["build", "test"]
    assert response.policy_decision.metadata_sanitized["phase_negotiation"]["can_start_initial_phase"] is True


def test_target_agent_missing_capability_reports_missing_capabilities(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, run = _run(kernel, "lucio")

    response = service.create_delegation(
        "lucio",
        run.run_id,
        DelegationCreateRequest(
            target_agent_id="codex",
            user_goal="Request unsupported governed capability.",
            requested_operation="technical_analysis",
            capabilities_requested=["read_workspace", "vision_pipeline"],
            risk_level="low",
        ),
    )

    assert response.status == "blocked"
    assert response.delegation.child_run_id is None
    assert response.result.metadata_sanitized["missing_capabilities"] == ["vision_pipeline"]
    assert response.result.metadata_sanitized["whether_execution_started"] is False
    assert response.result.metadata_sanitized["target_agent_declared_capabilities"]


def test_workspace_allowed_but_capability_blocked_is_reported_correctly(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, run = _run(kernel, "gemini")

    response = service.create_delegation(
        "gemini",
        run.run_id,
        DelegationCreateRequest(
            target_agent_id="aipinho",
            user_goal="Allowed workspace but unsupported target capability.",
            requested_operation="readonly_analysis",
            workspace_id="allowed_workspace",
            capabilities_requested=["read_workspace", "unknown_future_capability"],
            risk_level="low",
        ),
    )

    assert response.status == "blocked"
    assert response.result.metadata_sanitized["workspace_policy_decision"] == "governed"
    assert response.result.metadata_sanitized["missing_capabilities"] == ["unknown_future_capability"]
    assert response.result.metadata_sanitized["whether_execution_started"] is False


def test_high_risk_requires_approval_without_child_run(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, run = _run(kernel, "lucio")
    response = service.create_delegation(
        "lucio",
        run.run_id,
        DelegationCreateRequest(target_agent_id="codex", user_goal="High risk change", requested_operation="coding", capabilities_requested=["workspace_write"], risk_level="high"),
    )

    assert response.status == "approval_required"
    assert response.delegation.child_run_id is None
    assert response.policy_decision.approval_required is True
    assert kernel.get_run(run.run_id).status == "pending_approval"


def test_loop_protection_blocks_direct_cycle(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, parent = _run(kernel, "aipinho")
    first = service.create_delegation(
        "aipinho",
        parent.run_id,
        DelegationCreateRequest(target_agent_id="codex", user_goal="Code help", requested_operation="technical_analysis", capabilities_requested=["read_workspace"], risk_level="low"),
    )
    child_run_id = first.delegation.child_run_id
    assert child_run_id

    cycle = service.create_delegation(
        "codex",
        child_run_id,
        DelegationCreateRequest(target_agent_id="aipinho", user_goal="Loop back", requested_operation="local_execution", capabilities_requested=["read_workspace"], risk_level="low"),
    )

    assert cycle.status == "blocked"
    assert cycle.result.reason_code == "delegation_cycle_detected"


def test_cancel_and_timeout_update_parent_and_child(tmp_path):
    service, kernel, _ = _service(tmp_path)
    _, run = _run(kernel, "gemini")
    response = service.create_delegation(
        "gemini",
        run.run_id,
        DelegationCreateRequest(target_agent_id="aipinho", user_goal="Local read", requested_operation="readonly_analysis", capabilities_requested=["read_workspace"], risk_level="low", timeout_seconds=1),
    )
    child_run_id = response.delegation.child_run_id
    assert child_run_id

    cancelled = service.cancel(response.delegation.delegation_id)
    assert cancelled.status == "cancelled"
    assert kernel.get_run(child_run_id).status == "cancelled"

    _, run2 = _run(kernel, "gemini")
    timed = service.create_delegation(
        "gemini",
        run2.run_id,
        DelegationCreateRequest(target_agent_id="aipinho", user_goal="Local read", requested_operation="readonly_analysis", capabilities_requested=["read_workspace"], risk_level="low", timeout_seconds=1),
    )
    old = timed.delegation.model_copy(update={"created_at": (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()})
    service.store.save_request(old)
    timeout_response = service.check_timeout(timed.delegation.delegation_id)
    assert timeout_response.status == "timed_out"
    assert timeout_response.result.reason_code == "delegation_timeout"


def test_child_run_tool_gateway_keeps_delegation_trace(tmp_path):
    service, kernel, config = _service(tmp_path)
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
    _, parent = _run(kernel, "aipinho")
    delegated = service.create_delegation(
        "aipinho",
        parent.run_id,
        DelegationCreateRequest(target_agent_id="codex", user_goal="Create test file", requested_operation="coding", capabilities_requested=["workspace_write"], workspace_id="target", risk_level="medium"),
    )
    child_run_id = delegated.delegation.child_run_id
    assert child_run_id
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
    result = gateway.invoke("codex", child_run_id, "create_file", ToolInvocationCreateRequest(workspace_id="target", input={"relative_path": "ok.txt", "content": "ok"}))

    assert result.status == "succeeded"
    assert result.tool_invocation.delegation_id == delegated.delegation.delegation_id
    assert result.tool_invocation.parent_run_id == parent.run_id
    assert f"delegation:{delegated.delegation.delegation_id}" in result.tool_invocation.metadata_sanitized.values() or result.tool_invocation.delegation_id
    events = kernel.list_run_events(child_run_id, include_hidden=True)
    assert any(event.delegation_id == delegated.delegation.delegation_id for event in events if event.tool_invocation_id)
