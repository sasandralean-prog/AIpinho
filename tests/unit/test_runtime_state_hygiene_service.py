from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.delegation import DelegationRequest
from aipinho.schemas.agents.tool_gateway import PolicyDecision, ToolInvocation
from aipinho.services.agents.agent_delegation_store import AgentDelegationStore
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService
from aipinho.services.agents.multi_agent_policy_audit_store import MultiAgentPolicyAuditStore
from aipinho.services.runtime.health_semantics_service import HealthSemanticsService
from aipinho.services.runtime.runtime_state_hygiene_service import RuntimeStateHygieneService


def test_runtime_hygiene_preview_and_apply_marks_stale_run_without_deleting_evidence(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="stale"))
    old_started = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    run = kernel.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(operation_type="test", status="running", metadata_sanitized={"seed": "stale"}),
    )
    store.save_run(run.model_copy(update={"started_at": old_started}))
    service = RuntimeStateHygieneService(store=store, kernel=kernel)

    preview = service.preview(max_age_hours=24)
    result = service.apply(str(preview["preview_id"]))
    updated = store.get_run(run.run_id)

    assert preview["candidate_count"] >= 1
    assert result["applied_count"] >= 1
    assert result["deletes_evidence"] is False
    assert updated is not None
    assert updated.status == "cancelled"
    assert updated.error_code == "stale_runtime_cleanup"


def test_runtime_hygiene_preview_can_filter_candidate_kinds(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="stale session"))
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    store.update_session(session.model_copy(update={"updated_at": old_timestamp}))
    run = kernel.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(operation_type="test", status="running", metadata_sanitized={"seed": "stale"}),
    )
    store.save_run(run.model_copy(update={"started_at": old_timestamp}))
    delegations = AgentDelegationStore(tmp_path / "delegations")
    delegations.save_request(
        DelegationRequest(
            parent_agent_id="aipinho",
            target_agent_id="codex",
            parent_session_id=session.session_id,
            parent_run_id="missing_parent_run",
            child_run_id="missing_child_run",
            user_goal="active orphan",
            requested_operation="analysis",
            operation_type="analysis",
            status="running",
        )
    )
    service = RuntimeStateHygieneService(store=store, kernel=kernel, delegations=delegations)

    preview = service.preview(max_age_hours=24, kinds=["run", "delegation"])

    assert preview["kinds"] == ["delegation", "run"]
    assert {item["kind"] for item in preview["candidates"]} == {"run", "delegation"}


def test_runtime_hygiene_reconciles_active_orphan_delegation_without_deleting_evidence(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    delegations = AgentDelegationStore(tmp_path / "delegations")
    delegation = delegations.save_request(
        DelegationRequest(
            parent_agent_id="aipinho",
            target_agent_id="codex",
            parent_session_id="missing_parent_session",
            parent_run_id="missing_parent_run",
            child_run_id="missing_child_run",
            user_goal="active orphan",
            requested_operation="analysis",
            operation_type="analysis",
            status="running",
        )
    )
    service = RuntimeStateHygieneService(store=store, kernel=kernel, delegations=delegations)

    preview = service.preview(max_age_hours=24)
    result = service.apply(str(preview["preview_id"]))
    updated = delegations.get_request(delegation.delegation_id)
    saved_result = delegations.get_result(delegation.delegation_id)

    assert any(item["kind"] == "delegation" for item in preview["candidates"])
    assert any(item["kind"] == "delegation" for item in result["applied"])
    assert result["deletes_evidence"] is False
    assert updated is not None
    assert updated.status == "cancelled"
    assert saved_result is not None
    assert saved_result.reason_code == "orphan_delegation_cleanup"


def test_health_semantics_does_not_report_backend_offline_when_api_is_serving() -> None:
    status = HealthSemanticsService().status()

    assert status["backend_health"]["status"] == "online"
    assert status["backend_health"]["source"] == "api_liveness"
    assert status["operational_health"]["status"] == "ok"


def test_terminal_delegation_with_missing_run_refs_is_historical_info_not_degraded(tmp_path: Path) -> None:
    delegations = AgentDelegationStore(tmp_path / "delegations")
    delegations.save_request(
        DelegationRequest(
            parent_agent_id="aipinho",
            target_agent_id="codex",
            parent_session_id="missing_parent_session",
            parent_run_id="missing_parent_run",
            child_run_id="missing_child_run",
            user_goal="historical",
            requested_operation="analysis",
            operation_type="analysis",
            status="completed",
        )
    )
    service = MultiAgentObservabilityService(
        sessions=AgentSessionStore(tmp_path / "agent_kernel"),
        delegations=delegations,
        tools=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        policy_audit=MultiAgentPolicyAuditStore(tmp_path / "policy_kernel"),
    )

    report = service.state_consistency()

    assert report.status == "ok"
    assert {issue.severity for issue in report.issues} == {"info"}


def test_active_delegation_with_missing_run_refs_still_degrades(tmp_path: Path) -> None:
    delegations = AgentDelegationStore(tmp_path / "delegations")
    delegations.save_request(
        DelegationRequest(
            parent_agent_id="aipinho",
            target_agent_id="codex",
            parent_session_id="missing_parent_session",
            parent_run_id="missing_parent_run",
            child_run_id="missing_child_run",
            user_goal="active",
            requested_operation="analysis",
            operation_type="analysis",
            status="running",
        )
    )
    service = MultiAgentObservabilityService(
        sessions=AgentSessionStore(tmp_path / "agent_kernel"),
        delegations=delegations,
        tools=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        policy_audit=MultiAgentPolicyAuditStore(tmp_path / "policy_kernel"),
    )

    report = service.state_consistency()

    assert report.status == "degraded"
    assert {issue.severity for issue in report.issues} == {"warning"}


def test_terminal_tool_invocation_with_missing_run_is_historical_info_not_degraded(tmp_path: Path) -> None:
    tools = AgentToolInvocationStore(tmp_path / "tool_gateway")
    tools.save_invocation(
        ToolInvocation(
            run_id="missing_run",
            session_id="session_x",
            agent_id="codex",
            tool_name="sandbox_write_file",
            capability="sandbox_file_write",
            operation_type="create_file",
            input_summary_sanitized="historical terminal invocation",
            status="succeeded",
        )
    )
    service = MultiAgentObservabilityService(
        sessions=AgentSessionStore(tmp_path / "agent_kernel"),
        delegations=AgentDelegationStore(tmp_path / "delegations"),
        tools=tools,
        policy_audit=MultiAgentPolicyAuditStore(tmp_path / "policy_kernel"),
    )

    report = service.state_consistency()

    assert report.status == "ok"
    assert {issue.issue_type for issue in report.issues} == {"tool_without_run"}
    assert {issue.severity for issue in report.issues} == {"info"}


def test_active_tool_invocation_with_missing_run_still_degrades(tmp_path: Path) -> None:
    tools = AgentToolInvocationStore(tmp_path / "tool_gateway")
    tools.save_invocation(
        ToolInvocation(
            run_id="missing_run",
            session_id="session_x",
            agent_id="codex",
            tool_name="sandbox_write_file",
            capability="sandbox_file_write",
            operation_type="create_file",
            input_summary_sanitized="active orphan invocation",
            status="running",
        )
    )
    service = MultiAgentObservabilityService(
        sessions=AgentSessionStore(tmp_path / "agent_kernel"),
        delegations=AgentDelegationStore(tmp_path / "delegations"),
        tools=tools,
        policy_audit=MultiAgentPolicyAuditStore(tmp_path / "policy_kernel"),
    )

    report = service.state_consistency()

    assert report.status == "degraded"
    assert {issue.issue_type for issue in report.issues} == {"tool_without_run"}
    assert {issue.severity for issue in report.issues} == {"warning"}


def test_terminal_run_is_not_reported_active_due_to_old_running_event(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="terminal"))
    run = kernel.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(operation_type="create_file", status="completed", validation_status="passed"),
    )
    kernel.add_event(
        run.run_id,
        AgentEventCreateRequest(
            event_type="old_running_event",
            status="running",
            severity="info",
            human_message="Evento antigo de execucao.",
        ),
    )
    service = MultiAgentObservabilityService(
        sessions=store,
        delegations=AgentDelegationStore(tmp_path / "delegations"),
        tools=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        policy_audit=MultiAgentPolicyAuditStore(tmp_path / "policy_kernel"),
    )

    dashboard = service.dashboard()

    assert all(item["run_id"] != run.run_id for item in dashboard.active_runs)


def test_dashboard_treats_active_work_as_info_and_terminal_failures_as_history(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="observability semantics"))
    kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="analysis", status="running"))
    kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="analysis", status="failed"))
    service = MultiAgentObservabilityService(
        sessions=store,
        delegations=AgentDelegationStore(tmp_path / "delegations"),
        tools=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        policy_audit=MultiAgentPolicyAuditStore(tmp_path / "policy_kernel"),
    )

    cards = {card.card_id: card for card in service.dashboard().cards}

    assert cards["multi_agent_active_runs"].status == "running"
    assert cards["multi_agent_active_runs"].severity == "info"
    assert cards["multi_agent_failures"].status == "historical"
    assert cards["multi_agent_failures"].severity == "warning"


def test_dashboard_deduplicates_pending_approval_from_run_and_policy(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="approval dedup"))
    run = kernel.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(operation_type="create_file", status="pending_approval"),
    )
    policy_audit = MultiAgentPolicyAuditStore(tmp_path / "policy_kernel")
    policy_audit.save_policy_decision(
        PolicyDecision(
            agent_id="aipinho",
            session_id=session.session_id,
            run_id=run.run_id,
            operation_type="create_file",
            capability="workspace_write",
            decision="require_approval",
            reason_code="approval_required",
            human_reason="A escrita exige aprovacao.",
            technical_reason_sanitized="approval_required",
            approval_required=True,
        )
    )
    service = MultiAgentObservabilityService(
        sessions=store,
        delegations=AgentDelegationStore(tmp_path / "delegations"),
        tools=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        policy_audit=policy_audit,
    )

    dashboard = service.dashboard()

    assert len(dashboard.pending_approvals) == 1
    assert dashboard.pending_approvals[0]["run_id"] == run.run_id



def test_stale_running_run_is_marked_and_slot_released(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="slot release"))
    old_started = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="analysis", status="running"))
    store.save_run(run.model_copy(update={"started_at": old_started}))
    service = RuntimeStateHygieneService(store=store, kernel=kernel)

    preview = service.preview(max_age_hours=1, kinds=["run"])
    result = service.apply(str(preview["preview_id"]))
    updated = store.get_run(run.run_id)
    event_types = [event.event_type for event in store.list_events(run.run_id, include_hidden=True, limit=1000)]

    assert result["applied_count"] == 1
    assert updated is not None
    assert updated.status == "cancelled"
    assert "run_marked_stale" in event_types
    assert "run_slot_released" in event_types


def test_completed_at_non_terminal_run_is_not_counted_as_active(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("gemini", AgentSessionCreateRequest(title="completed timestamp"))
    run = kernel.create_run("gemini", session.session_id, AgentRunCreateRequest(operation_type="gemini_chat", status="created"))
    store.save_run(run.model_copy(update={"completed_at": datetime.now(timezone.utc).isoformat()}))
    service = MultiAgentObservabilityService(
        sessions=store,
        delegations=AgentDelegationStore(tmp_path / "delegations"),
        tools=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        policy_audit=MultiAgentPolicyAuditStore(tmp_path / "policy_kernel"),
    )

    dashboard = service.dashboard()

    assert all(item["run_id"] != run.run_id for item in dashboard.active_runs)


def test_dispatcher_health_reports_worker_slots(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="queue health"))
    old_started = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    for _ in range(2):
        run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="analysis", status="running"))
        store.save_run(run.model_copy(update={"started_at": old_started}))
    service = RuntimeStateHygieneService(store=store, kernel=kernel)

    health = service.queue_health(max_age_hours=1, worker_pool_capacity=2)

    assert health["active_runs"] == 2
    assert health["stale_runs"] == 2
    assert health["dispatcher_status"] == "stale_runs_detected"
    assert health["worker_pool_available_slots"] == 2
    assert health["reason_code"] == "stale_runs_detected"


def test_session_reaper_expires_inactive_sessions(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path / "agent_kernel")
    kernel = AgentSessionKernelService(store=store)
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="inactive"))
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    store.update_session(session.model_copy(update={"updated_at": old_timestamp}))
    service = RuntimeStateHygieneService(store=store, kernel=kernel)

    preview = service.preview(max_age_hours=24, kinds=["session"])
    result = service.apply(str(preview["preview_id"]))
    updated = store.get_session("aipinho", session.session_id, include_deleted=True)

    assert result["applied_count"] == 1
    assert updated is not None
    assert updated.archived is True
    assert updated.deleted is False
